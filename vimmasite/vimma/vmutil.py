from django.db import transaction

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (
    Provider, VM,
    PowerLog,
)
from vimma.util import (
    retry_transaction,
    vm_at_now, discard_expired_schedule_override,
)
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


def create_vm(vmconfig, project, schedule, comment, data, user_id=None):
    """
    Create a new VM, return its ID if successful otherwise throw an exception.

    The user is only needed to record in an audit message. Permission checking
    has already been done elsewhere.
    The data arg is specific to the provider type.
    This function must not be called inside a transaction.
    """
    aud.debug(('Request to create VM: ' +
        'config {vmconfig.id} ({vmconfig.name}), ' +
        'project {project.id} ({project.name}’), ' +
        'schedule {schedule.id} ({schedule.name}), ' +
        'comment ‘{comment}’, data ‘{data}’').format(
            vmconfig=vmconfig, project=project, schedule=schedule,
            comment=comment, data=data),
        user_id=user_id)
    # The transaction guarantees that if the vmtype.* call fails, the generic
    # VM object won't be present in the DB.
    callables = []
    with transaction.atomic():
        prov = vmconfig.provider
        vm = VM.objects.create(provider=prov, project=project,
                schedule=schedule, comment=comment)
        vm.full_clean()
        vm_id = vm.id

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
    return vm_id


def get_vm_controller(vm_id):
    """
    Return an instace of a VMController subclass, specific to the vm_id.
    """
    def get_prov_type():
        with transaction.atomic():
            return VM.objects.get(id=vm_id).provider.type
    t = retry_transaction(get_prov_type)
    if t == Provider.TYPE_DUMMY:
        return DummyVMController(vm_id)
    elif t == Provider.TYPE_AWS:
        return AWSVMController(vm_id)
    else:
        raise ValueError('Unknown provider type “{}”'.format(t))


class VMController():
    """
    Base class showing common VM operations.

    Use get_vm_controller(…) to obtain a vm-type-specific instance.
    """

    def __init__(self, vm_id):
        """
        An instance of this class is specific to a VM id.
        """
        self.vm_id = vm_id

    def power_on(self, user_id=None):
        raise NotImplementedError()

    def power_off(self, user_id=None):
        raise NotImplementedError()

    def reboot(self, user_id=None):
        raise NotImplementedError()

    def destroy(self, user_id=None):
        raise NotImplementedError()

    def update_status(self):
        raise NotImplementedError()


class DummyVMController(VMController):
    """
    VMController for vms of type dummy.
    """

    def power_on(self, user_id=None):
        vimma.vmtype.dummy.power_on_vm.delay(self.vm_id, user_id=user_id)

    def power_off(self, user_id=None):
        vimma.vmtype.dummy.power_off_vm.delay(self.vm_id, user_id=user_id)

    def reboot(self, user_id=None):
        vimma.vmtype.dummy.reboot_vm.delay(self.vm_id, user_id=user_id)

    def destroy(self, user_id=None):
        vimma.vmtype.dummy.destroy_vm.delay(self.vm_id, user_id=user_id)

    def update_status(self):
        vimma.vmtype.dummy.update_vm_status.delay(self.vm_id)


class AWSVMController(VMController):
    """
    VMController for AWS vms.
    """

    def power_on(self, user_id=None):
        vimma.vmtype.aws.power_on_vm.delay(self.vm_id, user_id=user_id)

    def power_off(self, user_id=None):
        vimma.vmtype.aws.power_off_vm.delay(self.vm_id, user_id=user_id)

    def reboot(self, user_id=None):
        vimma.vmtype.aws.reboot_vm.delay(self.vm_id, user_id=user_id)

    def destroy(self, user_id=None):
        vimma.vmtype.aws.destroy_vm.delay(self.vm_id, user_id=user_id)

    def update_status(self):
        vimma.vmtype.aws.update_vm_status.delay(self.vm_id)


@app.task
def update_all_vms_status():
    """
    Schedule tasks to check & update the state of each VM.

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

    with aud.ctx_mgr(vm_id=vm_id):
        get_vm_controller(vm_id).update_status()


def power_log(vm_id, powered_on):
    """
    PowerLog the current vm state (ON/OFF).
    """
    def do_log():
        with transaction.atomic():
            vm = VM.objects.get(id=vm_id)
            PowerLog.objects.create(vm=vm, powered_on=powered_on)

    with aud.ctx_mgr(vm_id=vm_id):
        if type(powered_on) is not bool:
            raise ValueError('powered_on ‘{}’ has type ‘{}’, want ‘{}’'.format(
                powered_on, type(powered_on), bool))

        retry_transaction(do_log)


def switch_on_off(vm_id, powered_on):
    """
    Power on/off the vm if needed.

    powered_on must be a boolean showing the current vm state.
    If the vm's power state should be different, a power_on or power_off task
    is submitted.
    """
    with aud.ctx_mgr(vm_id=vm_id):
        if type(powered_on) is not bool:
            raise ValueError('powered_on ‘{}’ has type ‘{}’, want ‘{}’'.format(
                powered_on, type(powered_on), bool))

        # clean-up, but not required
        discard_expired_schedule_override(vm_id)

        new_power_state = vm_at_now(vm_id)
        if powered_on is new_power_state:
            return

        if new_power_state:
            get_vm_controller(vm_id).power_on()
        else:
            get_vm_controller(vm_id).power_off()
