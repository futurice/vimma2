import datetime
from django.conf import settings
from django.db import transaction
from django.utils.timezone import utc

from vimma.actions import Actions
from vimma.audit import Auditor
from vimma.celery import app
import vimma.expiry
from vimma.models import (
    Provider, User,
    VM, Expiration, VMExpiration,
    FirewallRule,
)
from vimma.util import (
    can_do, retry_in_transaction,
)


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


@app.task
def update_all_vms_status():
    """
    Schedule tasks to check & update the state of each VM.

    These tasks get the VM status from the (remote) provider and update the
    VM object.
    """
    aud.debug('Update status of all non-destroyed VMs')
    for model in VM.implementations():
        vms = model.objects.filter(destroyed_at=None)
        for vm in vms:
            aud.debug('Request status update', vm_id=vm.pk)
            vm.controller().update_status()


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
