import boto.ec2
from django.db import transaction
import sys
import traceback

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (
    VM,
    AWSVMConfig, AWSVM,
)
from vimma.util import retry_transaction


aud = Auditor(__name__)


def connect_to_aws_vm_region(aws_vm_id):
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


def create_vm(vmconfig, vm, data, user_id=None):
    """
    Create an AWS VM from vmconfig & data, linking to parent ‘vm’.
    
    Returns (aws_vm, callables).
    data = {
        region: string,
    }

    This function must be called inside a transaction. The caller must execute
    the returned callables only after committing.
    """
    aws_vm_config = vmconfig.awsvmconfig

    aws_vm = AWSVM.objects.create(vm=vm, region=data['region'])
    aws_vm.full_clean()

    callables = [lambda: do_create_vm.delay(aws_vm_config.id, aws_vm.id,
        user_id)]
    return aws_vm, callables



@app.task
def do_create_vm(aws_vm_config_id, aws_vm_id, user_id):
    try:
        do_create_vm_impl(aws_vm_config_id, aws_vm_id, user_id)
    except:
        msg = traceback.format_exc()
        aud.error(msg, user_id=user_id)

        def set_status_error():
            with transaction.atomic():
                aws_vm = AWSVM.objects.get(id=aws_vm_id)
                # ideally:
                # lines = traceback.format_exception_only(*sys.exc_info()[:2])
                # msg = ''.join(lines)
                # aws_vm.status = msg[:status_field.max_length]

                # FIXME: Audit not status
                #aws_vm.status = 'Error (check logs)'

                aws_vm.save()
        retry_transaction(set_status_error)

        raise


def do_create_vm_impl(aws_vm_config_id, aws_vm_id, user_id):
    """
    The implementation for the similarly named task.

    This function provides the functionality, the task does exception handling.
    """
    # Make the API calls only once. Retrying failed DB transactions must only
    # include idempotent code, not the AWS API calls which create more VMs.

    access_key_id, access_key_secret = None, None
    region, ami_id, instance_type = None, None, None
    vm_id = None

    def read_vars():
        nonlocal access_key_id, access_key_secret
        nonlocal region, ami_id, instance_type
        nonlocal vm_id
        with transaction.atomic():
            aws_vm_config = AWSVMConfig.objects.get(id=aws_vm_config_id)
            aws_prov = aws_vm_config.vmconfig.provider.awsprovider
            aws_vm = AWSVM.objects.get(id=aws_vm_id)
            vm_id = aws_vm.vm.id

            access_key_id = aws_prov.access_key_id
            access_key_secret = aws_prov.access_key_secret

            region = aws_vm.region
            ami_id = aws_vm_config.ami_id
            instance_type = aws_vm_config.instance_type
    read_vars()

    conn = boto.ec2.connect_to_region(region,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=access_key_secret)
    reservation = conn.run_instances(ami_id,
            instance_type=instance_type)

    aud.info('Created AWS VM', user_id=user_id, vm_id=vm_id)

    # By now, the DB state (e.g. fields we don't care about) may have changed.
    # Don't overwrite the DB with our stale field values (from before the API
    # calls). Instead, read&update the DB.

    def update_db():
        with transaction.atomic():
            aws_vm = AWSVM.objects.get(id=aws_vm_id)
            aws_vm.reservation_id = reservation.id
            aws_vm.instance_id = reservation.instances[0].id
            aws_vm.save()
    retry_transaction(update_db)


def power_on_vm(vm_id, data, user_id=None):
    """
    Power on VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.
    """
    def read_db():
        with transaction.atomic():
            return VM.objects.get(id=vm_id).awsvm.id
    aws_vm_id = retry_transaction(read_db)

    do_power_on_vm.delay(aws_vm_id, user_id)


@app.task
def do_power_on_vm(aws_vm_id, user_id):
    with transaction.atomic():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        inst_id = aws_vm.instance_id
        vm_id = aws_vm.vm.id
        del aws_vm

    conn = connect_to_aws_vm_region(aws_vm_id)
    conn.start_instances(instance_ids=[inst_id])
    aud.info('Started instance', vm_id=vm_id, user_id=user_id)


def power_off_vm(vm_id, data, user_id=None):
    """
    Power off VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.
    """
    def read_db():
        with transaction.atomic():
            return VM.objects.get(id=vm_id).awsvm.id
    aws_vm_id = retry_transaction(read_db)

    do_power_off_vm.delay(aws_vm_id, user_id=user_id)


@app.task
def do_power_off_vm(aws_vm_id, user_id=None):
    with transaction.atomic():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        inst_id = aws_vm.instance_id
        vm_id = aws_vm.vm.id
        del aws_vm

    conn = connect_to_aws_vm_region(aws_vm_id)
    conn.stop_instances(instance_ids=[inst_id])
    aud.info('Stopped instance', vm_id=vm_id, user_id=user_id)


def reboot_vm(vm_id, data, user_id=None):
    """
    Reboot VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.
    """
    def read_db():
        with transaction.atomic():
            return VM.objects.get(id=vm_id).awsvm.id
    aws_vm_id = retry_transaction(read_db)

    do_reboot_vm.delay(aws_vm_id, user_id=user_id)


@app.task
def do_reboot_vm(aws_vm_id, user_id=None):
    with transaction.atomic():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        inst_id = aws_vm.instance_id
        vm_id = aws_vm.vm.id
        del aws_vm

    conn = connect_to_aws_vm_region(aws_vm_id)
    conn.reboot_instances(instance_ids=[inst_id])
    aud.info('Rebooted instance', vm_id=vm_id, user_id=user_id)


def destroy_vm(vm_id, data, user_id=None):
    """
    Destroy VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.
    """
    def read_db():
        with transaction.atomic():
            return VM.objects.get(id=vm_id).awsvm.id
    aws_vm_id = retry_transaction(read_db)

    do_destroy_vm.delay(aws_vm_id, user_id=user_id)


@app.task
def do_destroy_vm(aws_vm_id, user_id=None):
    with transaction.atomic():
        aws_vm = AWSVM.objects.get(id=aws_vm_id)
        inst_id = aws_vm.instance_id
        vm_id = aws_vm.vm.id
        del aws_vm

    conn = connect_to_aws_vm_region(aws_vm_id)
    conn.terminate_instances(instance_ids=[inst_id])
    aud.info('Destroyed instance', vm_id=vm_id, user_id=user_id)


@app.task
def update_vm_status(vm_id):
    def read_data():
        with transaction.atomic():
            aws_vm = VM.objects.get(id=vm_id).awsvm
            return aws_vm.id, aws_vm.instance_id
    aws_vm_id, inst_id = retry_transaction(read_data)

    if not inst_id:
        aud.warn('missing instance_id', vm_id=vm_id)
        return

    conn = connect_to_aws_vm_region(aws_vm_id)
    instances = conn.get_only_instances(instance_ids=[inst_id])
    if len(instances) != 1:
        aud.warn('AWS returned {} instances, expected 1'.format(len(instances)),
                vm_id=vm_id)
        new_state = 'Error'
    else:
        new_state = instances[0].state

    def write_data():
        with transaction.atomic():
            aws_vm = AWSVM.objects.get(id=aws_vm_id)
            aws_vm.state = new_state
            aws_vm.save()
    retry_transaction(write_data)
