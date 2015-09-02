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
    discard_expired_schedule_override,
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


@app.task
def update_all_vms_status():
    """
    Schedule tasks to check & update the state of each VM.

    These tasks get the VM status from the (remote) provider and update the
    VM object.
    """
    aud.debug('Update status of all non-destroyed VMs')
    for model in VM.implementations():
        vm = model.objects.filter(destroyed_at=None)
        aud.debug('Request status update', vm_id=vm.pk)
        vm.controller().update_status()




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
