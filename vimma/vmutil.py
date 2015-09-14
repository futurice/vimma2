import datetime
from django.conf import settings
from django.db import transaction
from django.utils.timezone import utc

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (VM, Expiration)

aud = Auditor(__name__)

@app.task
def update_all_vms_status():
    """
    Schedule tasks to check & update the state of each VM.

    These tasks get the VM status from the (remote) provider and update the
    VM object.
    """
    aud.debug('Update status of all non-destroyed VMs')
    for model in VM.implementations():
        for vm in model.objects.filter(destroyed_at=None):
            aud.debug('Request status update', vm_id=vm.pk)
            vm.controller().update_status()

@app.task
def expiration_grace_action(cls, vm_id):
    with aud.ctx_mgr(vm_id=vm_id):
        vm = cls.objects.get(id=vm_id)
        exp_date = vm.expiration.expires_at
        aud.warning('Performing action at the end of grace period for VM ' +
                'which expired on ' + str(exp_date),
                vm_id=vm.id)
        vm.controller().destroy()

@app.task
def dispatch_all_expiration_notifications():
    aud.debug('Check which Expiration items need a notification')
    with aud.ctx_mgr():
        for model in Expiration.implementations():
            for match in model.objects.filter(grace_end_action_performed=False):
                if match.expiration_controller().needs_notification():
                    match.expiration_controller().notify()

@app.task
def dispatch_all_expiration_grace_end_actions():
    aud.debug('Check which Expiration items need a grace-end action')
    with aud.ctx_mgr():
        for model in Expiration.implementations():
            for match in model.objects.filter(grace_end_action_performed=False):
                if match.expiration_controller().needs_grace_end_action():
                    match.expiration_controller().perform_grace_end_action

