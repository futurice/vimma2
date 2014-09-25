import logging
from django.db import transaction

from vimma.celery import app
from vimma.models import (
    Provider, VM,
)
import vimma.vmtype.dummy


log = logging.getLogger(__name__)


def create_vm(vmconfig, project, schedule, data):
    """
    Create and return a new VM or throw an exception.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    log.info(('Create VM: config ‘{.name}’, project ‘{.name}’, ' +
        'schedule ‘{.name}’, data ‘{}’').format(vmconfig, project, schedule,
            data))
    callables = []
    with transaction.atomic():
        prov = vmconfig.provider
        vm = VM.objects.create(provider=prov, project=project,
                schedule=schedule)
        vm.full_clean()

        if prov.type == Provider.TYPE_DUMMY:
            dvm, callables = vimma.vmtype.dummy.create_vm(vm, data)
        else:
            raise ValueError('Unknown provider type “{}”'.format(prov.type))

    for c in callables:
        c()
    return vm


def power_on_vm(vm, data):
    """
    Power ON VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    # In the general case, the type-specific function will modify data (e.g.
    # set the state to ‘requesting power on…’) and return callbacks (e.g.
    # celery tasks). The callbacks must run after the data modifications have
    # been committed, not the other way around (i.e. overwriting the callback
    # results such as ‘powered on’ with ‘requesting power on…’).
    #
    # For this same reason, the other similar functions have the same
    # transaction-related requirement.
    log.info('Power ON VM ‘{.id}’, data ‘{}’'.format(vm, data))
    callables = []
    with transaction.atomic():
        t = vm.provider.type
        if t == Provider.TYPE_DUMMY:
            callables = vimma.vmtype.dummy.power_on_vm(vm, data)
        else:
            raise ValueError('Unknown provider type “{}”'.format(t))

    for c in callables:
        c()


def power_off_vm(vm, data):
    """
    Power OFF VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    log.info('Power OFF VM ‘{.id}’, data ‘{}’'.format(vm, data))
    callables = []
    with transaction.atomic():
        t = vm.provider.type
        if t == Provider.TYPE_DUMMY:
            callables = vimma.vmtype.dummy.power_off_vm(vm, data)
        else:
            raise ValueError('Unknown provider type “{}”'.format(t))

    for c in callables:
        c()


def reboot_vm(vm, data):
    """
    Reboot VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    log.info('Reboot VM ‘{.id}’, data ‘{}’'.format(vm, data))
    callables = []
    with transaction.atomic():
        t = vm.provider.type
        if t == Provider.TYPE_DUMMY:
            callables = vimma.vmtype.dummy.reboot_vm(vm, data)
        else:
            raise ValueError('Unknown provider type “{}”'.format(t))

    for c in callables:
        c()


def destroy_vm(vm, data):
    """
    Destroy VM.

    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    log.info('Destroy VM ‘{.id}’, data ‘{}’'.format(vm, data))
    callables = []
    with transaction.atomic():
        t = vm.provider.type
        if t == Provider.TYPE_DUMMY:
            callables = vimma.vmtype.dummy.destroy_vm(vm, data)
        else:
            raise ValueError('Unknown provider type “{}”'.format(t))

    for c in callables:
        c()


@app.task
def update_all_vms_status():
    """
    Schedule tasks to check & update the state on each VM.

    These tasks get the VM status from the (remote) provider and update the
    VM object.
    """
    with transaction.atomic():
        for vm in VM.objects.filter():
            # don't allow a single VM to break the loop, e.g. with missing
            # foreign keys. Make a separate task for each instead of handling
            # all in this task.
            update_vm_status.delay(vm.id)


@app.task
def update_vm_status(vm_id):
    """
    Check & update the status of the VM.
    """
    with transaction.atomic():
        vm = VM.objects.get(id=vm_id)
        t = vm.provider.type
        if t == Provider.TYPE_DUMMY:
            vimma.vmtype.dummy.update_vm_status.delay(vm.dummyvm.id)
        else:
            log.error('Unknown provider type “{}”'.format(t))
