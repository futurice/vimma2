from vimma.celery import app
from vimma.audit import Auditor

from aws.models import VM
# TODO: circular: from aws.controller import ec2_connect_to_aws_vm_region

@app.task
def do_create_vm(aws_vm_config_id, root_device_size, root_device_volume_type,
        vm_id, user_id):
    do_create_vm_impl(aws_vm_config_id, root_device_size,
            root_device_volume_type, vm_id, user_id)

@app.task
def power_on_vm(vm_id, user_id=None):
    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        vm = VM.objects.get(id=vm_id)
        conn = ec2_connect_to_aws_vm_region(vm.pk)
        conn.start_instances(instance_ids=[vm.instance_id])
        vm.auditor.info('Started instance', user_id=user_id)
        route53_add.delay(vm.pk, user_id=user_id)


@app.task
def power_off_vm(vm_id, user_id=None):
    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        vm = VM.objects.get(id=vm_id)
        conn = ec2_connect_to_aws_vm_region(vm.pk)
        conn.stop_instances(instance_ids=[vm.instance_id])
        vm.auditor.info('Stopped instance', user_id=user_id)


@app.task
def reboot_vm(vm_id, user_id=None):
    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        vm = VM.objects.get(id=vm_id)
        conn = ec2_connect_to_aws_vm_region(vm.pk)
        conn.reboot_instances(instance_ids=[vm.instance_id])
        vm.auditor.info('Rebooted instance', user_id=user_id)


@app.task
def destroy_vm(vm_id, user_id=None):
    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        vm = VM.objects.get(id=vm_id)
        terminate_instance.delay(vm_id, user_id=user_id)
        delete_security_group.delay(vm_id, user_id=user_id)
        route53_delete.delay(vm_id, user_id=user_id)
        vm.auditor.info('Scheduled destruction tasks', user_id=user_id)

def mark_vm_destroyed_if_needed(vm):
    """
    Mark the parent .vm model destroyed if the awsvm is destroyed, else no-op.

    This function may only be called inside a transaction.
    """
    if vm.instance_terminated and vm.security_group_deleted:
        vm.destroyed_at = datetime.datetime.utcnow().replace(tzinfo=utc)
        vm.save()

@app.task(bind=True, max_retries=15, default_retry_delay=60)
def delete_security_group(self, vm_id, user_id=None):
    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'delete security group', **aud_kw):
        vm = VM.objects.get(id=vm_id)
        if vm.security_group_id:
            conn = ec2_connect_to_aws_vm_region(vm.pk)
            conn.delete_security_group(group_id=vm.security_group_id)
        vm.security_group_deleted = True
        vm.save()
        mark_vm_destroyed_if_needed(vm)
        vm.auditor.info('Deleted security group {}'.format(vm.security_group_id), user_id=user_id)


@app.task(bind=True, max_retries=30, default_retry_delay=10)
def terminate_instance(self, vm_id, user_id=None):
    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'terminate instance', **aud_kw):
        vm = VM.objects.get(id=vm_id)
        if vm.instance_id:
            conn = ec2_connect_to_aws_vm_region(vm.pk)
            conn.terminate_instances(instance_ids=[vm.instance_id])
        vm.instance_terminated = True
        vm.save()
        mark_vm_destroyed_if_needed(vm)
        vm.auditor.info('Terminated instance {}'.format(vm.instance_id), user_id=user_id)


@app.task
def update_vm_status(vm_id):
    vm = VM.objects.get(id=vm_id)

    conn = ec2_connect_to_aws_vm_region(vm.pk)
    instances = conn.get_only_instances(instance_ids=[vm.pk])
    if len(instances) != 1:
        vm.auditor.warning('Returned {} instances, expected 1'.format(len(instances)))
        new_state = 'Error'
        new_ip_address = None
        new_private_ip_address = None
    else:
        inst = instances[0]
        new_state = inst.state
        new_ip_address = inst.ip_address
        new_private_ip_address = inst.private_ip_address

    vm.state = new_state
    vm.ip_address = new_ip_address or ''
    vm.private_ip_address = new_private_ip_address or ''
    vm.save()
    vm.auditor.debug('Update state ‘{}’'.format(new_state))

    vm.controller().set_vm_status_updated_at_now()

    powered_on = VM().isOn(new_state)
    vm.controller().power_log(powered_on)
    if new_state != 'terminated':
        vm.controller().switch_on_off(powered_on)


@app.task(bind=True, max_retries=12, default_retry_delay=10)
def route53_add(self, vm_id, user_id=None):
    """
    Write a CNAME in the Public DNS Zone and an A record in the Private Zone.

    This task does 2 things (CNAME and A). If any fails, the entire task is
    retried.
    """
    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'add route53 cname', **aud_kw):
        vm = VM.objects.get(id=vm_id)
        vm_cname = (vm.name + '.' + vm.config.provider.route_53_zone).lower()

        ec2_conn = ec2_connect_to_aws_vm_region(vm.pk)
        instances = ec2_conn.get_only_instances(instance_ids=[vm.instance_id])
        if len(instances) != 1:
            vm.auditor.warning(' returned {} instances, expected 1'.format(
                len(instances)), user_id=user_id)
            self.retry()
        instance = instances[0]

        r53_conn = route53_connect_to_aws_vm_region(vm.pk)
        priv_zone, pub_zone = None, None
        for z in r53_conn.get_zones():
            if z.name != vm.config.provider.route_53_zone:
                continue
            if z.config['PrivateZone'] == 'true':
                priv_zone = z
            elif z.config['PrivateZone'] == 'false':
                pub_zone = z

        if pub_zone:
            pub_dns_name = instance.public_dns_name
            if not pub_dns_name:
                vm.auditor.warning('No public DNS name for instance {}'.format(
                    vm.instance_id), user_id=user_id)
                self.retry()

            if pub_zone.get_cname(vm_cname, all=True):
                pub_zone.delete_cname(vm_cname, all=True)
                vm.auditor.info('Removed existing DNS cname ‘{}’'.format(vm_cname), user_id=user_id)
            pub_zone.add_cname(vm_cname, pub_dns_name,
                    comment='Vimma-generated')
            vm.auditor.info('Created DNS cname ‘{}’'.format(vm_cname), user_id=user_id)
        else:
            vm.auditor.warning('No public DNS zone named ‘{}’'.format(vm.config.provider.route_53_zone),
                    user_id=user_id)

        if priv_zone:
            priv_ip = instance.private_ip_address
            if not priv_ip:
                vm.auditor.warning('No private IP address for instance{}'.format(
                    vm.instance_id), user_id=user_id)
                self.retry()

            if priv_zone.get_a(vm_cname, all=True):
                priv_zone.delete_a(vm_cname, all=True)
                vm.auditor.info('Removed existing A record ‘{}’'.format(vm_cname),
                        user_id=user_id)
            priv_zone.add_a(vm_cname, priv_ip, comment='Vimma-generated')
            vm.auditor.info('Created A record ‘{}’ {}'.format(vm_cname, priv_ip),
                        user_id=user_id)
        else:
            vm.auditor.warning('No private DNS zone named ‘{}’'.format(vm.config.provider.route_53_zone),
                        user_id=user_id)


@app.task(bind=True, max_retries=24, default_retry_delay=5)
def route53_delete(self, vm_id, user_id=None):
    """
    Delete a CNAME in the Public DNS Zone and an A record in the Private Zone.

    This task does 2 things (CNAME and A). If any fails, the entire task is
    retried.
    """
    aud_kw = {'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'delete route53 cname', **aud_kw):
        vm = VM.objects.get(id=vm_id)
        vm_cname = (vm.name + '.' + vm.config.provider.route_53_zone).lower()

        r53_conn = route53_connect_to_aws_vm_region(vm.pk)
        priv_zone, pub_zone = None, None
        for z in r53_conn.get_zones():
            if z.name != vm.config.provider.route_53_zone:
                continue
            if z.config['PrivateZone'] == 'true':
                priv_zone = z
            elif z.config['PrivateZone'] == 'false':
                pub_zone = z

        if pub_zone:
            if pub_zone.get_cname(vm_cname, all=True):
                pub_zone.delete_cname(vm_cname, all=True)
                vm.auditor.info('Removed DNS cname ‘{}’'.format(vm_cname), **aud_kw)
            else:
                vm.auditor.warning('DNS cname ‘{}’ does not exist'.format(vm_cname),
                        **aud_kw)
        else:
            vm.auditor.warning('No public DNS zone named ‘{}’'.format(vm.config.provider.route_53_zone),
                    **aud_kw)

        if priv_zone:
            if priv_zone.get_a(vm_cname, all=True):
                priv_zone.delete_a(vm_cname, all=True)
                vm.auditor.info('Removed A record ‘{}’'.format(vm_cname), **aud_kw)
            else:
                vm.auditor.warning('DNS A record ‘{}’ does not exist'.format(
                    vm_cname), **aud_kw)
        else:
            vm.auditor.warning('No private DNS zone named ‘{}’'.format(vm.config.provider.route_53_zone),
                    **aud_kw)

