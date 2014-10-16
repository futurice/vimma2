from django.db import transaction

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (
    Provider, VM,
)
from vimma.util import retry_transaction
import vimma.vmtype.dummy, vimma.vmtype.aws


aud = Auditor(__name__)


# The following pattern is used, especially for Celery tasks:
#
# with transaction.atomic():
#   read & write to the db
#   Don't leak any Model objects outside this block, only assign primitive
#   values (e.g. int, string) to names outside this block. This way we always
#   read & write consistent data (ACID transactions) and we don't accidentaly
#   do DB operations outside the atomic block (e.g. by accessing model fields
#   or related models).
#
# Often retrying the transaction.


def create_vm(vmconfig, project, schedule, data, user_id=None):
    """
    Create and return a new VM or throw an exception.

    The user is only needed to record in an audit message. Permission checking
    has already been done elsewhere.
    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    aud.debug(('Request to create VM: config ‘{.name}’, project ‘{.name}’, ' +
        'schedule ‘{.name}’, data ‘{}’').format(vmconfig, project, schedule,
            data), user_id=user_id)
    # The transaction guarantees that if the vmtype.* call fails, the generic
    # VM object won't be present in the DB.
    callables = []
    with transaction.atomic():
        prov = vmconfig.provider
        vm = VM.objects.create(provider=prov, project=project,
                schedule=schedule)
        vm.full_clean()

        t = prov.type
        if t == Provider.TYPE_DUMMY:
            dvm, callables = vimma.vmtype.dummy.create_vm(vm, data,
                    user_id=user_id)
        elif t == Provider.TYPE_AWS:
            awsvm, callables = vimma.vmtype.aws.create_vm(vmconfig, vm, data,
                    user_id=user_id)
        else:
            raise ValueError('Unknown provider type “{}”'.format(prov.type))

    for c in callables:
        c()
    return vm


def power_on_vm(vm, data, user_id=None):
    """
    Power ON VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    # In the general case, the type-specific function will modify data (e.g.
    # set the state to ‘requesting power on…’) and schedule (celery) tasks.
    # The tasks must run after the data modifications have been committed, not
    # the other way around (i.e. overwriting the task results such as
    # ‘powered on’ with ‘requesting power on…’).
    #
    # For this reason, the other similar functions have the same
    # transaction-related requirement (so they can commit the data themselves
    # before scheduling the task).
    #
    # Unlike create_vm(), this function doesn't make DB writes which must be
    # undone if the vmtype.* call fails. So not starting a transaction here.
    # Although both this function and the callee access related DB data.
    aud.debug('Request to Power ON, data ‘{}’'.format(data),
            vm_id=vm.id, user_id=user_id)
    t = vm.provider.type
    if t == Provider.TYPE_DUMMY:
        vimma.vmtype.dummy.power_on_vm(vm.id, data, user_id=user_id)
    elif t == Provider.TYPE_AWS:
        vimma.vmtype.aws.power_on_vm(vm.id, data, user_id=user_id)
    else:
        raise ValueError('Unknown provider type “{}”'.format(t))


def power_off_vm(vm, data, user_id=None):
    """
    Power OFF VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    aud.debug('Request to Power OFF, data ‘{}’'.format(data),
            vm_id=vm.id, user_id=user_id)
    t = vm.provider.type
    if t == Provider.TYPE_DUMMY:
        vimma.vmtype.dummy.power_off_vm(vm.id, data, user_id=user_id)
    elif t == Provider.TYPE_AWS:
        vimma.vmtype.aws.power_off_vm(vm.id, data, user_id=user_id)
    else:
        raise ValueError('Unknown provider type “{}”'.format(t))


def reboot_vm(vm, data, user_id=None):
    """
    Reboot VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    aud.debug('Request to Reboot, data ‘{}’'.format(data),
            vm_id=vm.id, user_id=user_id)
    t = vm.provider.type
    if t == Provider.TYPE_DUMMY:
        vimma.vmtype.dummy.reboot_vm(vm.id, data, user_id=user_id)
    elif t == Provider.TYPE_AWS:
        vimma.vmtype.aws.reboot_vm(vm.id, data, user_id=user_id)
    else:
        raise ValueError('Unknown provider type “{}”'.format(t))


def destroy_vm(vm, data, user_id=None):
    """
    Destroy VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    aud.debug('Request to Destroy, data ‘{}’'.format(data),
            vm_id=vm.id, user_id=user_id)
    t = vm.provider.type
    if t == Provider.TYPE_DUMMY:
        vimma.vmtype.dummy.destroy_vm(vm.id, data, user_id=user_id)
    elif t == Provider.TYPE_AWS:
        vimma.vmtype.aws.destroy_vm(vm.id, data, user_id=user_id)
    else:
        raise ValueError('Unknown provider type “{}”'.format(t))


@app.task
def update_all_vms_status():
    """
    Schedule tasks to check & update the state on each VM.

    These tasks get the VM status from the (remote) provider and update the
    VM object.
    """
    aud.debug('Update status of all VMs')
    with transaction.atomic():
        vm_ids = map(lambda v: v.id, VM.objects.filter())
    for x in vm_ids:
        # don't allow a single VM to break the loop, e.g. with missing
        # foreign keys. Make a separate task for each instead of handling
        # all in this task.
        update_vm_status.delay(x)


@app.task
def update_vm_status(vm_id):
    """
    Check & update the status of the VM.
    """
    aud.debug('Request status update', vm_id=vm_id)

    def get_type():
        with transaction.atomic():
            vm = VM.objects.get(id=vm_id)
            return vm.provider.type
    t = retry_transaction(get_type)

    if t == Provider.TYPE_DUMMY:
        vimma.vmtype.dummy.update_vm_status.delay(vm_id)
    elif t == Provider.TYPE_AWS:
        vimma.vmtype.aws.update_vm_status.delay(vm_id)
    else:
        aud.error('Unknown provider type “{}”'.format(t), vm_id=vm_id)
