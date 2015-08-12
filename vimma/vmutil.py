import datetime
from django.conf import settings
from django.db import transaction
from django.utils.timezone import utc

from vimma.actions import Actions
from vimma.audit import Auditor
from vimma.celery import app
import vimma.expiry
from vimma.models import (
    Provider, VM, User,
    Expiration, VMExpiration,
    PowerLog,
    FirewallRule,
)
from vimma.util import (
    can_do, retry_in_transaction,
    vm_at_now, discard_expired_schedule_override,
    get_import
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


def create_vm(vmconfig, project, schedule, comment, data, user_id):
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
        user = User.objects.get(id=user_id)
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        sched_override_tstamp = (now.timestamp() +
                settings.VM_CREATION_OVERRIDE_SECS)

        expire_dt = now + datetime.timedelta(seconds=settings.DEFAULT_VM_EXPIRY_SECS)

        vmexp = VMExpiration.objects.create(expires_at=expire_dt)
        vm = VM.objects.create(provider=prov, project=project,
                schedule=schedule, sched_override_state=True,
                sched_override_tstamp=sched_override_tstamp,
                comment=comment, created_by=user, expiration=vmexp)
        vm.full_clean()
        vm_id = vm.id

        t = prov.type
        if t == Provider.TYPE_DUMMY:
            dvm, callables = vimma.vmtype.dummy.create_vm(vm, data, user_id)
        elif t == Provider.TYPE_AWS:
            awsvm, callables = vimma.vmtype.aws.create_vm(vmconfig, vm, data,
                    user_id)
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
        return VM.objects.get(id=vm_id).provider.type
    t = retry_in_transaction(get_prov_type)
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
        """
        This method is responsible for the following actions (e.g. schedule
        them as asynchronous tasks):
        Get the VM status from the remote provider, save it in the Vimma DB and
        mark the timestamp of this update.
        Call power_log() to log the current power state (on or off).
        Call switch_on_off() which turns the vm on or off if needed.
        """
        raise NotImplementedError()

    def can_change_firewall_rules(self, user_id):
        def call():
            user = User.objects.get(id=user_id)
            vm = VM.objects.get(id=self.vm_id)
            return can_do(user, Actions.CREATE_VM_IN_PROJECT, vm.project)
        return retry_in_transaction(call)

    def create_firewall_rule(self, data, user_id=None):
        """
        Create a firewall rule with data specific to the vm type.
        """
        raise NotImplementedError()

    def delete_firewall_rule(self, fw_rule_id, user_id=None):
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

    def create_firewall_rule(self, data, user_id=None):
        vimma.vmtype.aws.create_firewall_rule(self.vm_id, data,
                user_id=user_id)

    def delete_firewall_rule(self, fw_rule_id, user_id=None):
        vimma.vmtype.aws.delete_firewall_rule(fw_rule_id, user_id=user_id)


@app.task
def update_all_vms_status():
    """
    Schedule tasks to check & update the state of each VM.

    These tasks get the VM status from the (remote) provider and update the
    VM object.
    """
    aud.debug('Update status of all non-destroyed VMs')
    with transaction.atomic():
        vm_ids = map(lambda v: v.id, VM.objects.filter(destroyed_at=None))
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
        vm = VM.objects.get(id=vm_id)
        PowerLog.objects.create(vm=vm, powered_on=powered_on)

    with aud.ctx_mgr(vm_id=vm_id):
        if type(powered_on) is not bool:
            raise ValueError('powered_on ‘{}’ has type ‘{}’, want ‘{}’'.format(
                powered_on, type(powered_on), bool))

        retry_in_transaction(do_log)


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

        # TODO: maybe move this to the update status task
        # clean-up, but not required
        discard_expired_schedule_override(vm_id)

        new_power_state = vm_at_now(vm_id)
        if powered_on is new_power_state:
            return

        if new_power_state:
            get_vm_controller(vm_id).power_on()
        else:
            get_vm_controller(vm_id).power_off()


@app.task
def expiration_notify(vm_id):
    """
    Notify of vm expiration.
    """
    with aud.ctx_mgr(vm_id=vm_id):
        def read():
            vm = VM.objects.get(id=vm_id)
            return vm.expiration.expires_at
        exp_date = retry_in_transaction(read)
        aud.warning('Notify of VM expiration on ' + str(exp_date),
                vm_id=vm_id)


@app.task
def expiration_grace_action(vm_id):
    """
    Perform the action at the end of the vm's grace period.
    """
    with aud.ctx_mgr(vm_id=vm_id):
        def read():
            vm = VM.objects.get(id=vm_id)
            return vm.expiration.expires_at
        exp_date = retry_in_transaction(read)
        aud.warning('Performing action at the end of grace period for VM ' +
                'which expired on ' + str(exp_date),
                vm_id=vm_id)
        get_vm_controller(vm_id).destroy()


@app.task
def dispatch_all_expiration_notifications():
    """
    Check which Expiration items need a notification and run controller.notify.
    """
    aud.debug('Check which Expiration items need a notification')
    with aud.ctx_mgr():
        for model in Expiration.implementations():
            for match in model.objects.filter(grace_end_action_performed=False):
                dispatch_expiration_notification.delay(model, match.pk)

@app.task
def dispatch_expiration_notification(exp_id):
    """
    Check the Expiration item and notify if needed.
    """
    aud.debug('Checking if Expiration id ' + str(exp_id) +
            ' needs a notification')

    with aud.ctx_mgr():
        c = vimma.expiry.get_controller(exp_id)
        if c.needs_notification():
            c.notify()


@app.task
def dispatch_all_expiration_grace_end_actions():
    """
    Check which Expiration items need a grace-end action and run it.
    """
    aud.debug('Check which Expiration items need a grace-end action')
    with aud.ctx_mgr():
        for model in Expiration.implementations():
            for match in model.objects.filter(grace_end_action_performed=False):
                dispatch_expiration_grace_end_action.delay(model, match.pk)

@app.task
def dispatch_expiration_grace_end_action(model, exp_id):
    """
    Check the Expiration item and perform the grace end action if needed.
    """
    aud.debug('Checking if Expiration id ' + str(exp_id) +
            ' needs a grace-end action')
    with aud.ctx_mgr():
        c = vimma.expiry.get_controller(model, exp_id)
        if c.needs_grace_end_action():
            c.perform_grace_end_action()


def delete_firewall_rule(fw_rule_id, user_id=None):
    def get_vm_id():
        fw_rule = FirewallRule.objects.get(id=fw_rule_id)
        return fw_rule.vm.id
    vm_id = retry_in_transaction(get_vm_id)

    get_vm_controller(vm_id).delete_firewall_rule(fw_rule_id, user_id=user_id)
