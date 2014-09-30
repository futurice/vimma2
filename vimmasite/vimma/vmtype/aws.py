import boto.ec2
from django.db import transaction
import logging
import sys
import traceback

from vimma.celery import app
from vimma.models import (
    AWSVMConfig, AWSVM,
)
from vimma.util import retry_transaction


log = logging.getLogger(__name__)


def create_vm(vmconfig, vm, data):
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

    aws_vm = AWSVM.objects.create(vm=vm, status='scheduled for creation…',
            region=data['region'])
    aws_vm.full_clean()

    callables = [lambda: do_create_vm.delay(aws_vm_config.id, aws_vm.id)]
    return aws_vm, callables



@app.task
def do_create_vm(aws_vm_config_id, aws_vm_id):
    try:
        do_create_vm_impl(aws_vm_config_id, aws_vm_id)
    except:
        msg = traceback.format_exc()
        log.error(msg)

        def set_status_error():
            with transaction.atomic():
                aws_vm = AWSVM.objects.get(id=aws_vm_id)
                # ideally:
                # msg = traceback.format_exception_only(*sys.exc_info()[:2])
                # aws_vm.status = msg[:status_field.max_length]
                aws_vm.status = 'Error (check logs)'
                aws_vm.save()
        retry_transaction(set_status_error)

        raise


def do_create_vm_impl(aws_vm_config_id, aws_vm_id):
    """
    The implementation for the similarly named task.

    This function provides the functionality, the task does exception handling.
    """
    # Make the API calls only once. Retrying failed DB transactions must only
    # include idempotent code, not the AWS API calls which create more VMs.

    access_key_id, access_key_secret = None, None
    region, ami_id, instance_type = None, None, None

    def read_vars():
        nonlocal access_key_id, access_key_secret
        nonlocal region, ami_id, instance_type
        with transaction.atomic():
            aws_vm_config = AWSVMConfig.objects.get(id=aws_vm_config_id)
            aws_prov = aws_vm_config.vmconfig.provider.awsprovider
            aws_vm = AWSVM.objects.get(id=aws_vm_id)

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
