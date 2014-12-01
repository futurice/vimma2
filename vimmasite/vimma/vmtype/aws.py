import base64
import boto.ec2
import boto.route53
import celery.exceptions
import datetime
from django.db import transaction
from django.utils.timezone import utc
import sys
import traceback

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (
    VM,
    AWSVMConfig, AWSVM,
)
from vimma.util import retry_transaction, set_vm_status_updated_at_now
import vimma.vmutil


aud = Auditor(__name__)


def ec2_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto EC2Connection to the given AWS VM's region.
    """
    def read_data():
        with transaction.atomic():
            aws_vm = AWSVM.objects.get(id=aws_vm_id)
            aws_prov = aws_vm.vm.provider.awsprovider

            return (aws_prov.access_key_id, aws_prov.access_key_secret,
                    aws_vm.region)
    access_key_id, access_key_secret, region = retry_transaction(read_data)

    return boto.ec2.connect_to_region(region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret)


def route53_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto Route53Connection to the given AWS VM's region.
    """
    def read_data():
        with transaction.atomic():
            aws_vm = AWSVM.objects.get(id=aws_vm_id)
            aws_prov = aws_vm.vm.provider.awsprovider

            return (aws_prov.access_key_id, aws_prov.access_key_secret,
                    aws_vm.region)
    access_key_id, access_key_secret, region = retry_transaction(read_data)

    return boto.route53.connect_to_region(region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret)


def create_vm(vmconfig, vm, data, user_id):
    """
    Create an AWS VM from vmconfig & data, linking to parent ‘vm’.
    
    Returns (aws_vm, callables).
    data = {
        name: string,
    }

    This function must be called inside a transaction. The caller must execute
    the returned callables only after committing.
    """
    aws_vm_config = vmconfig.awsvmconfig

    aws_vm = AWSVM.objects.create(vm=vm, name=data['name'],
            region=aws_vm_config.region)
    aws_vm.full_clean()

    callables = [lambda: do_create_vm.delay(aws_vm_config.id, vm.id, user_id)]
    return aws_vm, callables


@app.task
def do_create_vm(aws_vm_config_id, vm_id, user_id):
    try:
        do_create_vm_impl(aws_vm_config_id, vm_id, user_id)
    except:
        msg = ''.join(traceback.format_exc())
        aud.error(msg, vm_id=vm_id, user_id=user_id)
        destroy_vm.delay(vm_id, user_id=user_id)
        raise


def do_create_vm_impl(aws_vm_config_id, vm_id, user_id):
    """
    The implementation for the similarly named task.

    This function provides the functionality, the task does exception handling.
    """
    # Make the API calls only once. Retrying failed DB transactions must only
    # include idempotent code, not the AWS API calls which create more VMs.

    ssh_key_name, default_security_group_id = None, None
    aws_vm_id, name = None, None
    ami_id, instance_type, user_data = None, None, None

    def read_vars():
        nonlocal ssh_key_name, default_security_group_id
        nonlocal aws_vm_id, name
        nonlocal ami_id, instance_type, user_data
        with transaction.atomic():
            aws_vm_config = AWSVMConfig.objects.get(id=aws_vm_config_id)
            aws_prov = aws_vm_config.vmconfig.provider.awsprovider
            vm = VM.objects.get(id=vm_id)
            aws_vm = vm.awsvm

            ssh_key_name = aws_prov.ssh_key_name
            default_security_group_id = aws_prov.default_security_group_id

            aws_vm_id = aws_vm.id
            name = aws_vm.name
            ami_id = aws_vm_config.ami_id
            instance_type = aws_vm_config.instance_type

            user_data = base64.b64encode(
                    aws_prov.user_data.format(vm=vm).encode('utf-8'))
    retry_transaction(read_vars)

    ec2_conn = ec2_connect_to_aws_vm_region(aws_vm_id)

    security_group = ec2_conn.create_security_group(
            '{}-{}'.format(name, vm_id), 'Vimma-generated')
    sec_grp_id = security_group.id

    def write_sec_grp():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm.security_group_id = sec_grp_id
            aws_vm.save()
    retry_transaction(write_sec_grp)

    security_group_ids = [sec_grp_id]
    if default_security_group_id:
        security_group_ids.append(default_security_group_id)
    reservation = ec2_conn.run_instances(ami_id,
            instance_type=instance_type,
            security_group_ids=security_group_ids,
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
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm.reservation_id = reservation.id
            aws_vm.instance_id = inst_id
            aws_vm.save()
    retry_transaction(update_db)

    if inst:
        inst.add_tags({
            'Name': name,
            'VimmaSpawned': str(True),
        })

    route53_add.delay(vm_id, user_id=user_id)


@app.task
def power_on_vm(vm_id, user_id=None):
    def read_vars():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm_id = aws_vm.id
            inst_id = aws_vm.instance_id
            return aws_vm_id, inst_id

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        aws_vm_id, inst_id = retry_transaction(read_vars)
        conn = ec2_connect_to_aws_vm_region(aws_vm_id)
        conn.start_instances(instance_ids=[inst_id])
        aud.info('Started instance', vm_id=vm_id, user_id=user_id)
        route53_add.delay(vm_id, user_id=user_id)


@app.task
def power_off_vm(vm_id, user_id=None):
    def read_vars():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm_id = aws_vm.id
            inst_id = aws_vm.instance_id
            return aws_vm_id, inst_id

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        aws_vm_id, inst_id = retry_transaction(read_vars)
        conn = ec2_connect_to_aws_vm_region(aws_vm_id)
        conn.stop_instances(instance_ids=[inst_id])
        aud.info('Stopped instance', vm_id=vm_id, user_id=user_id)
        route53_delete.delay(vm_id, user_id=user_id)


@app.task
def reboot_vm(vm_id, user_id=None):
    def read_vars():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm_id = aws_vm.id
            inst_id = aws_vm.instance_id
            return aws_vm_id, inst_id

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        aws_vm_id, inst_id = retry_transaction(read_vars)
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
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm_id = aws_vm.id
            sec_grp_id = aws_vm.security_group_id
            return aws_vm_id, sec_grp_id

    def write_security_group_deleted():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm.security_group_deleted = True
            aws_vm.full_clean()
            aws_vm.save()
            mark_vm_destroyed_if_needed(aws_vm)

    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'delete security group', **aud_kw):
        aws_vm_id, sec_grp_id = retry_transaction(read_vars)
        # check if the VM creation failed to create the security group
        if sec_grp_id:
            conn = ec2_connect_to_aws_vm_region(aws_vm_id)
            conn.delete_security_group(group_id=sec_grp_id)
        retry_transaction(write_security_group_deleted)
    aud.info('Deleted security group {}'.format(sec_grp_id), **aud_kw)


@app.task(bind=True, max_retries=30, default_retry_delay=10)
def terminate_instance(self, vm_id, user_id=None):
    def read_vars():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm_id = aws_vm.id
            inst_id = aws_vm.instance_id
            return aws_vm_id, inst_id

    def write_instance_terminated():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            aws_vm.instance_terminated = True
            aws_vm.full_clean()
            aws_vm.save()
            mark_vm_destroyed_if_needed(aws_vm)

    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'terminate instance', **aud_kw):
        aws_vm_id, inst_id = retry_transaction(read_vars)
        # check if the VM creation failed to create the instance
        if inst_id:
            conn = ec2_connect_to_aws_vm_region(aws_vm_id)
            conn.terminate_instances(instance_ids=[inst_id])
        retry_transaction(write_instance_terminated)
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
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            return aws_vm.id, aws_vm.instance_id
    aws_vm_id, inst_id = retry_transaction(read_data)

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
        with transaction.atomic():
            aws_vm = AWSVM.objects.get(id=aws_vm_id)
            aws_vm.state = new_state
            aws_vm.ip_address = new_ip_address or ''
            aws_vm.save()
    retry_transaction(write_data)
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
    def read_vars():
        with transaction.atomic():
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
        aws_vm_id, name, inst_id, route_53_zone = retry_transaction(read_vars)

        ec2_conn = ec2_connect_to_aws_vm_region(aws_vm_id)
        instances = ec2_conn.get_only_instances(instance_ids=[inst_id])
        if len(instances) != 1:
            aud.warning('AWS returned {} instances, expected 1'.format(
                len(instances)), **aud_kw)
            self.retry()
        pub_dns_name = instances[0].public_dns_name
        if not pub_dns_name:
            aud.warning('No public DNS name for instance {}'.format(inst_id),
                    **aud_kw)
            self.retry()

        r53_conn = route53_connect_to_aws_vm_region(aws_vm_id)
        r53_z = r53_conn.get_zone(route_53_zone)

        vm_cname = (name + '.' + route_53_zone).lower()
        if r53_z.get_cname(vm_cname, all=True):
            r53_z.delete_cname(vm_cname, all=True)
            aud.info('Removed existing DNS cname ‘{}’'.format(vm_cname),
                    **aud_kw)
        r53_z.add_cname(vm_cname, pub_dns_name, comment='Vimma-generated')
        aud.info('Created DNS cname ‘{}’'.format(vm_cname), **aud_kw)


@app.task(bind=True, max_retries=24, default_retry_delay=5)
def route53_delete(self, vm_id, user_id=None):
    def read_vars():
        with transaction.atomic():
            vm = VM.objects.get(id=vm_id)
            aws_vm = vm.awsvm
            aws_vm_id = aws_vm.id
            name = aws_vm.name

            aws_prov = vm.provider.awsprovider
            route_53_zone = aws_prov.route_53_zone
            return aws_vm_id, name, route_53_zone

    aud_kw = {'vm_id': vm_id, 'user_id': user_id}
    with aud.celery_retry_ctx_mgr(self, 'delete route53 cname', **aud_kw):
        aws_vm_id, name, route_53_zone = retry_transaction(read_vars)

        r53_conn = route53_connect_to_aws_vm_region(aws_vm_id)
        r53_z = r53_conn.get_zone(route_53_zone)

        vm_cname = (name + '.' + route_53_zone).lower()
        if r53_z.get_cname(vm_cname, all=True):
            r53_z.delete_cname(vm_cname, all=True)
            aud.info('Removed DNS cname ‘{}’'.format(vm_cname), **aud_kw)
        else:
            aud.warning('DNS cname ‘{}’ does not exist'.format(vm_cname),
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
