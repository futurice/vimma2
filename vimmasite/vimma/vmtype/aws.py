import boto.ec2, boto.route53, boto.vpc
import celery.exceptions
import datetime
from django.conf import settings
from django.db import transaction
from django.utils.timezone import utc
import random
import sys
import traceback

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (
    VM,
    AWSVMConfig, AWSVM,
    FirewallRule, AWSFirewallRule,
    Expiration, FirewallRuleExpiration,
)
from vimma.util import retry_in_transaction, set_vm_status_updated_at_now
import vimma.vmutil


aud = Auditor(__name__)


def ec2_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto EC2Connection to the given AWS VM's region.
    """
    def read_data():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        aws_prov = aws_vm.vm.provider.awsprovider

        return (aws_prov.access_key_id, aws_prov.access_key_secret,
                aws_vm.region)
    access_key_id, access_key_secret, region = retry_in_transaction(read_data)

    return boto.ec2.connect_to_region(region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret)


def route53_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto Route53Connection to the given AWS VM's region.
    """
    def read_data():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        aws_prov = aws_vm.vm.provider.awsprovider

        return (aws_prov.access_key_id, aws_prov.access_key_secret,
                aws_vm.region)
    access_key_id, access_key_secret, region = retry_in_transaction(read_data)

    return boto.route53.connect_to_region(region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret)


def vpc_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto VPCConnection to the given AWS VM's region.
    """
    def read_data():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        aws_prov = aws_vm.vm.provider.awsprovider

        return (aws_prov.access_key_id, aws_prov.access_key_secret,
                aws_vm.region)
    access_key_id, access_key_secret, region = retry_in_transaction(read_data)

    return boto.vpc.connect_to_region(region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret)


def create_vm(vmconfig, vm, data, user_id):
    """
    Create an AWS VM from vmconfig & data, linking to parent ‘vm’.
    
    Returns (aws_vm, callables).
    data = {
        name: string,
        root_device_size: int,
        root_device_volume_type: string,
    }

    This function must be called inside a transaction. The caller must execute
    the returned callables only after committing.
    """
    root_device_size = data['root_device_size']
    if type(root_device_size) != int:
        raise ValueError('root_device_size must be int')
    if (root_device_size < settings.AWS_ROOT_DEVICE_MIN_SIZE or
            root_device_size > settings.AWS_ROOT_DEVICE_MAX_SIZE):
        raise ValueError('root_device_size must be between {} and {}'.format(
            settings.AWS_ROOT_DEVICE_MIN_SIZE,
            settings.AWS_ROOT_DEVICE_MAX_SIZE))

    root_device_volume_type = data['root_device_volume_type']
    if (root_device_volume_type not in
            [c[0] for c in AWSVMConfig.VOLUME_TYPE_CHOICES]):
        raise ValueError('Invalid root_device_volume_type value')

    aws_vm_config = vmconfig.awsvmconfig

    aws_vm = AWSVM.objects.create(vm=vm, name=data['name'],
            region=aws_vm_config.region)
    aws_vm.full_clean()

    callables = [lambda: do_create_vm.delay(aws_vm_config.id, root_device_size,
        root_device_volume_type, vm.id, user_id)]
    return aws_vm, callables


@app.task
def do_create_vm(aws_vm_config_id, root_device_size, root_device_volume_type,
        vm_id, user_id):
    try:
        do_create_vm_impl(aws_vm_config_id, root_device_size,
                root_device_volume_type, vm_id, user_id)
    except:
        msg = ''.join(traceback.format_exc())
        aud.error(msg, vm_id=vm_id, user_id=user_id)
        destroy_vm.delay(vm_id, user_id=user_id)
        raise


def do_create_vm_impl(aws_vm_config_id, root_device_size,
        root_device_volume_type, vm_id, user_id):
    """
    The implementation for the similarly named task.

    This function provides the functionality, the task does exception handling.
    """
    # Make the API calls only once. Retrying failed DB transactions must only
    # include idempotent code, not the AWS API calls which create more VMs.

    ssh_key_name, default_security_group_id, vpc_id = None, None, None
    aws_vm_id, name = None, None
    ami_id, instance_type, user_data = None, None, None

    def read_vars():
        nonlocal ssh_key_name, default_security_group_id, vpc_id
        nonlocal aws_vm_id, name
        nonlocal ami_id, instance_type, user_data
        aws_vm_config = AWSVMConfig.objects.get(id=aws_vm_config_id)
        aws_prov = aws_vm_config.vmconfig.provider.awsprovider
        vm = VM.objects.get(id=vm_id)
        aws_vm = vm.awsvm

        ssh_key_name = aws_prov.ssh_key_name
        default_security_group_id = aws_prov.default_security_group_id
        vpc_id = aws_prov.vpc_id

        aws_vm_id = aws_vm.id
        name = aws_vm.name
        ami_id = aws_vm_config.ami_id
        instance_type = aws_vm_config.instance_type

        user_data = aws_prov.user_data.format(vm=vm).encode('utf-8')
    retry_in_transaction(read_vars)

    ec2_conn = ec2_connect_to_aws_vm_region(aws_vm_id)

    security_group = ec2_conn.create_security_group(
            '{}-{}'.format(name, vm_id), 'Vimma-generated', vpc_id=vpc_id)
    sec_grp_id = security_group.id

    def write_sec_grp():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm.security_group_id = sec_grp_id
        aws_vm.save()
    retry_in_transaction(write_sec_grp)

    security_group_ids = [sec_grp_id]
    if default_security_group_id:
        security_group_ids.append(default_security_group_id)

    vpc_conn = vpc_connect_to_aws_vm_region(aws_vm_id)
    subnets = vpc_conn.get_all_subnets(filters={'vpcId': [vpc_id]})
    subnet_id = random.choice(subnets).id

    img = ec2_conn.get_image(ami_id)
    bdm = img.block_device_mapping
    # Passing the image's BDM to run_instances raises:
    # ‘Parameter encrypted is invalid. You cannot specify the encrypted flag if
    # specifying a snapshot id in a block device mapping’.
    # Un-set the offending flag(s): encrypted.
    bdm[img.root_device_name].size = root_device_size
    bdm[img.root_device_name].volume_type = root_device_volume_type
    for k in bdm:
        bdm[k].encrypted = None

    reservation = ec2_conn.run_instances(ami_id,
            instance_type=instance_type,
            security_group_ids=security_group_ids,
            subnet_id=subnet_id,
            block_device_map=bdm,
            key_name=ssh_key_name or None,
            user_data=user_data or None)

    aud.info('Got AWS reservation', user_id=user_id, vm_id=vm_id)

    inst = None
    inst_id = ''
    if len(reservation.instances) != 1:
        aud.error('AWS reservation has {} instances, expected 1'.format(
            len(reservation.instances)), user_id=user_id, vm_id=vm_id)
    else:
        inst = reservation.instances[0]
        inst_id = inst.id

    # By now, the DB state (e.g. fields we don't care about) may have changed.
    # Don't overwrite the DB with our stale field values (from before the API
    # calls). Instead, read&update the DB.

    def update_db():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm.reservation_id = reservation.id
        aws_vm.instance_id = inst_id
        aws_vm.save()
    retry_in_transaction(update_db)

    if inst:
        inst.add_tags({
            'Name': name,
            'VimmaSpawned': str(True),
        })

    route53_add.delay(vm_id, user_id=user_id)


@app.task
def power_on_vm(vm_id, user_id=None):
    def read_vars():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm_id = aws_vm.id
        inst_id = aws_vm.instance_id
        return aws_vm_id, inst_id

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        aws_vm_id, inst_id = retry_in_transaction(read_vars)
        conn = ec2_connect_to_aws_vm_region(aws_vm_id)
        conn.start_instances(instance_ids=[inst_id])
        aud.info('Started instance', vm_id=vm_id, user_id=user_id)
        route53_add.delay(vm_id, user_id=user_id)


@app.task
def power_off_vm(vm_id, user_id=None):
    def read_vars():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm_id = aws_vm.id
        inst_id = aws_vm.instance_id
        return aws_vm_id, inst_id

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        aws_vm_id, inst_id = retry_in_transaction(read_vars)
        conn = ec2_connect_to_aws_vm_region(aws_vm_id)
        conn.stop_instances(instance_ids=[inst_id])
        aud.info('Stopped instance', vm_id=vm_id, user_id=user_id)


@app.task
def reboot_vm(vm_id, user_id=None):
    def read_vars():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm_id = aws_vm.id
        inst_id = aws_vm.instance_id
        return aws_vm_id, inst_id

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        aws_vm_id, inst_id = retry_in_transaction(read_vars)
        conn = ec2_connect_to_aws_vm_region(aws_vm_id)
        conn.reboot_instances(instance_ids=[inst_id])
        aud.info('Rebooted instance', vm_id=vm_id, user_id=user_id)


@app.task
def destroy_vm(vm_id, user_id=None):
    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        terminate_instance.delay(vm_id, user_id=user_id)
        # can add countdown=…, but this task would still have to retry anyway
        delete_security_group.delay(vm_id, user_id=user_id)
        route53_delete.delay(vm_id, user_id=user_id)
    aud.info('Scheduled destruction tasks', vm_id=vm_id, user_id=user_id)


@app.task(bind=True, max_retries=15, default_retry_delay=60)
def delete_security_group(self, vm_id, user_id=None):
    def read_vars():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm_id = aws_vm.id
        sec_grp_id = aws_vm.security_group_id
        return aws_vm_id, sec_grp_id

    def write_security_group_deleted():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm.security_group_deleted = True
        aws_vm.full_clean()
        aws_vm.save()
        mark_vm_destroyed_if_needed(aws_vm)

    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'delete security group', **aud_kw):
        aws_vm_id, sec_grp_id = retry_in_transaction(read_vars)
        # check if the VM creation failed to create the security group
        if sec_grp_id:
            conn = ec2_connect_to_aws_vm_region(aws_vm_id)
            conn.delete_security_group(group_id=sec_grp_id)
        retry_in_transaction(write_security_group_deleted)
    aud.info('Deleted security group {}'.format(sec_grp_id), **aud_kw)


@app.task(bind=True, max_retries=30, default_retry_delay=10)
def terminate_instance(self, vm_id, user_id=None):
    def read_vars():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm_id = aws_vm.id
        inst_id = aws_vm.instance_id
        return aws_vm_id, inst_id

    def write_instance_terminated():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        aws_vm.instance_terminated = True
        aws_vm.full_clean()
        aws_vm.save()
        mark_vm_destroyed_if_needed(aws_vm)

    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'terminate instance', **aud_kw):
        aws_vm_id, inst_id = retry_in_transaction(read_vars)
        # check if the VM creation failed to create the instance
        if inst_id:
            conn = ec2_connect_to_aws_vm_region(aws_vm_id)
            conn.terminate_instances(instance_ids=[inst_id])
        retry_in_transaction(write_instance_terminated)
    aud.info('Terminated instance {}'.format(inst_id), **aud_kw)


@app.task
def update_vm_status(vm_id):
    with aud.ctx_mgr(vm_id=vm_id):
        _update_vm_status_impl(vm_id)

def _update_vm_status_impl(vm_id):
    """
    The implementation for the similarly named task.
    """
    def read_data():
        aws_vm = VM.objects.get(id=vm_id).awsvm
        return aws_vm.id, aws_vm.instance_id
    aws_vm_id, inst_id = retry_in_transaction(read_data)

    if not inst_id:
        aud.warning('missing instance_id', vm_id=vm_id)
        return

    conn = ec2_connect_to_aws_vm_region(aws_vm_id)
    instances = conn.get_only_instances(instance_ids=[inst_id])
    if len(instances) != 1:
        aud.warning('AWS returned {} instances, expected 1'.format(
            len(instances)), vm_id=vm_id)
        new_state = 'Error'
        new_ip_address = None
    else:
        inst = instances[0]
        new_state = inst.state
        new_ip_address = inst.ip_address

    def write_data():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        aws_vm.state = new_state
        aws_vm.ip_address = new_ip_address or ''
        aws_vm.save()
    retry_in_transaction(write_data)
    aud.debug('Update state ‘{}’'.format(new_state), vm_id=vm_id)

    set_vm_status_updated_at_now(vm_id)

    on_states = {'pending', 'running', 'stopping', 'shutting-down'}
    off_states = {'stopped', 'terminated'}
    powered_on = (True if new_state in on_states
            else False if new_state in off_states
            else None)
    if type(powered_on) is not bool:
        aud.info('Unknown vm state ‘{}’'.format(new_state), vm_id=vm_id)
        return
    vimma.vmutil.power_log(vm_id, powered_on)
    if new_state != 'terminated':
        vimma.vmutil.switch_on_off(vm_id, powered_on)


@app.task(bind=True, max_retries=12, default_retry_delay=10)
def route53_add(self, vm_id, user_id=None):
    """
    Write a CNAME in the Public DNS Zone and an A record in the Private Zone.

    This task does 2 things (CNAME and A). If any fails, the entire task is
    retried.
    """
    def read_vars():
        vm = VM.objects.get(id=vm_id)
        aws_vm = vm.awsvm
        aws_vm_id = aws_vm.id
        name = aws_vm.name
        inst_id = aws_vm.instance_id

        aws_prov = vm.provider.awsprovider
        route_53_zone = aws_prov.route_53_zone
        return aws_vm_id, name, inst_id, route_53_zone

    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'add route53 cname', **aud_kw):
        aws_vm_id, name, inst_id, route_53_zone = retry_in_transaction(
                read_vars)
        vm_cname = (name + '.' + route_53_zone).lower()

        ec2_conn = ec2_connect_to_aws_vm_region(aws_vm_id)
        instances = ec2_conn.get_only_instances(instance_ids=[inst_id])
        if len(instances) != 1:
            aud.warning('AWS returned {} instances, expected 1'.format(
                len(instances)), **aud_kw)
            self.retry()
        instance = instances[0]

        r53_conn = route53_connect_to_aws_vm_region(aws_vm_id)
        priv_zone, pub_zone = None, None
        for z in r53_conn.get_zones():
            if z.name != route_53_zone:
                continue
            if z.config['PrivateZone'] == 'true':
                priv_zone = z
            elif z.config['PrivateZone'] == 'false':
                pub_zone = z

        if pub_zone:
            pub_dns_name = instance.public_dns_name
            if not pub_dns_name:
                aud.warning('No public DNS name for instance {}'.format(
                    inst_id), **aud_kw)
                self.retry()

            if pub_zone.get_cname(vm_cname, all=True):
                pub_zone.delete_cname(vm_cname, all=True)
                aud.info('Removed existing DNS cname ‘{}’'.format(vm_cname),
                        **aud_kw)
            pub_zone.add_cname(vm_cname, pub_dns_name,
                    comment='Vimma-generated')
            aud.info('Created DNS cname ‘{}’'.format(vm_cname), **aud_kw)
        else:
            aud.warning('No public DNS zone named ‘{}’'.format(route_53_zone),
                    **aud_kw)

        if priv_zone:
            priv_ip = instance.private_ip_address
            if not priv_ip:
                aud.warning('No private IP address for instance{}'.format(
                    inst_id), **aud_kw)
                self.retry()

            if priv_zone.get_a(vm_cname, all=True):
                priv_zone.delete_a(vm_cname, all=True)
                aud.info('Removed existing A record ‘{}’'.format(vm_cname),
                        **aud_kw)
            priv_zone.add_a(vm_cname, priv_ip, comment='Vimma-generated')
            aud.info('Created A record ‘{}’ {}'.format(vm_cname, priv_ip),
                    **aud_kw)
        else:
            aud.warning('No private DNS zone named ‘{}’'.format(route_53_zone),
                    **aud_kw)


@app.task(bind=True, max_retries=24, default_retry_delay=5)
def route53_delete(self, vm_id, user_id=None):
    """
    Delete a CNAME in the Public DNS Zone and an A record in the Private Zone.

    This task does 2 things (CNAME and A). If any fails, the entire task is
    retried.
    """
    def read_vars():
        vm = VM.objects.get(id=vm_id)
        aws_vm = vm.awsvm
        aws_vm_id = aws_vm.id
        name = aws_vm.name

        aws_prov = vm.provider.awsprovider
        route_53_zone = aws_prov.route_53_zone
        return aws_vm_id, name, route_53_zone

    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'delete route53 cname', **aud_kw):
        aws_vm_id, name, route_53_zone = retry_in_transaction(read_vars)
        vm_cname = (name + '.' + route_53_zone).lower()

        r53_conn = route53_connect_to_aws_vm_region(aws_vm_id)
        priv_zone, pub_zone = None, None
        for z in r53_conn.get_zones():
            if z.name != route_53_zone:
                continue
            if z.config['PrivateZone'] == 'true':
                priv_zone = z
            elif z.config['PrivateZone'] == 'false':
                pub_zone = z

        if pub_zone:
            if pub_zone.get_cname(vm_cname, all=True):
                pub_zone.delete_cname(vm_cname, all=True)
                aud.info('Removed DNS cname ‘{}’'.format(vm_cname), **aud_kw)
            else:
                aud.warning('DNS cname ‘{}’ does not exist'.format(vm_cname),
                        **aud_kw)
        else:
            aud.warning('No public DNS zone named ‘{}’'.format(route_53_zone),
                    **aud_kw)

        if priv_zone:
            if priv_zone.get_a(vm_cname, all=True):
                priv_zone.delete_a(vm_cname, all=True)
                aud.info('Removed A record ‘{}’'.format(vm_cname), **aud_kw)
            else:
                aud.warning('DNS A record ‘{}’ does not exist'.format(
                    vm_cname), **aud_kw)
        else:
            aud.warning('No private DNS zone named ‘{}’'.format(route_53_zone),
                    **aud_kw)


def mark_vm_destroyed_if_needed(awsvm):
    """
    Mark the parent .vm model destroyed if the awsvm is destroyed, else no-op.

    This function may only be called inside a transaction.
    """
    if awsvm.instance_terminated and awsvm.security_group_deleted:
        vm = awsvm.vm
        vm.destroyed_at = datetime.datetime.utcnow().replace(tzinfo=utc)
        vm.full_clean()
        vm.save()


def create_firewall_rule(vm_id, data, user_id=None):
    """
    data: {
        ip_protocol: string,
        from_port: int,
        to_port: int,
        cidr_ip: string,
    }
    """
    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        with transaction.atomic():
            vm = VM.objects.get(id=vm_id)
            base_fw_rule = FirewallRule.objects.create(vm=vm)
            base_fw_rule.full_clean()

            ip_protocol = data['ip_protocol']
            from_port, to_port = data['from_port'], data['to_port']
            cidr_ip = data['cidr_ip']
            aws_fw_rule = AWSFirewallRule.objects.create(
                    firewallrule=base_fw_rule,
                    ip_protocol=ip_protocol,
                    from_port=from_port,
                    to_port=to_port,
                    cidr_ip=cidr_ip)
            aws_fw_rule.full_clean()

            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            expire_dt = now + datetime.timedelta(
                    seconds=settings.NORMAL_FIREWALL_RULE_EXPIRY_SECS
                    if not aws_fw_rule.is_special()
                    else settings.SPECIAL_FIREWALL_RULE_EXPIRY_SECS)
            expiration = Expiration.objects.create(
                    type=Expiration.TYPE_FIREWALL_RULE, expires_at=expire_dt)
            expiration.full_clean()
            FirewallRuleExpiration.objects.create(
                    expiration=expiration,
                    firewallrule=base_fw_rule).full_clean()

            awsvm = vm.awsvm
            conn = ec2_connect_to_aws_vm_region(awsvm.id)
            conn.authorize_security_group(group_id=awsvm.security_group_id,
                    ip_protocol=ip_protocol,
                    from_port=from_port,
                    to_port=to_port,
                    cidr_ip=cidr_ip)

        aud.info('Created a firewall rule', vm_id=vm_id, user_id=user_id)


def delete_firewall_rule(fw_rule_id, user_id=None):
    def get_vm_id():
        fw_rule = FirewallRule.objects.get(id=fw_rule_id)
        return fw_rule.vm.id
    vm_id = retry_in_transaction(get_vm_id)

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        fw_rule = FirewallRule.objects.get(id=fw_rule_id)
        afr = fw_rule.awsfirewallrule
        awsvm = fw_rule.vm.awsvm
        conn = ec2_connect_to_aws_vm_region(awsvm.id)
        conn.revoke_security_group(group_id=awsvm.security_group_id,
                ip_protocol=afr.ip_protocol,
                from_port=afr.from_port,
                to_port=afr.to_port,
                cidr_ip=afr.cidr_ip)
        fw_rule.delete()

    aud.info('Deleted a firewall rule', vm_id=vm_id, user_id=user_id)
