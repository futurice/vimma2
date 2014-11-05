from django.db import transaction

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (
    VM,
    DummyVM,
)
from vimma.util import retry_transaction
import vimma.vmutil


aud = Auditor(__name__)


def create_vm(vm, data, user_id=None):
    """
    Create a dummy VM, linking to parent ‘vm’, from ‘data’ → (vm, callables)

    data = {
        name: string,
        delay: int, // seconds before powering ON
    }

    This function must be called inside a transaction. The caller must execute
    the returned callables only after committing.
    """
    dummyVM = DummyVM.objects.create(vm=vm, name=data['name'])
    dummyVM.full_clean()

    aud.info('Created VM', user_id=user_id, vm_id=vm.id)

    # execute as much code as possible here (inside the transaction) not in the
    # callable (which runs after comitting the transaction).
    countdown = min(max(0, data['delay']), 60)
    callables = [
            lambda: power_on_vm.apply_async(args=(vm.id, user_id),
                countdown=countdown),
            ]
    return dummyVM, callables


@app.task
def power_on_vm(vm_id, user_id=None):
    def call():
        with transaction.atomic():
            dvm = VM.objects.get(id=vm_id).dummyvm
            # imagine this logic happens remotely, in an API call to Provider
            if dvm.destroyed or dvm.poweredon:
                aud.error(('Can\'t power on DummyVM {0.id} ‘{0.name}’ with ' +
                    'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
                    ).format(dvm), user_id=user_id, vm_id=vm_id)
                return
            dvm.poweredon = True
            dvm.save()

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        retry_transaction(call)
        aud.info('Power ON', user_id=user_id, vm_id=vm_id)


@app.task
def power_off_vm(vm_id, user_id=None):
    def call():
        with transaction.atomic():
            dvm = VM.objects.get(id=vm_id).dummyvm
            if dvm.destroyed or not dvm.poweredon:
                aud.error(('Can\'t power off DummyVM {0.id} ‘{0.name}’ with ' +
                    'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
                    ).format(dvm), user_id=user_id, vm_id=vm_id)
                return
            dvm.poweredon = False
            dvm.save()

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        retry_transaction(call)
        aud.info('Power OFF', user_id=user_id, vm_id=vm_id)


@app.task
def reboot_vm(vm_id, user_id=None):
    def call():
        with transaction.atomic():
            dvm = VM.objects.get(id=vm_id).dummyvm
            if dvm.destroyed:
                aud.error(('Can\'t reboot DummyVM {0.id} ‘{0.name}’ with ' +
                    'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
                    ).format(dvm), user_id=user_id, vm_id=vm_id)
                return
            dvm.poweredon = True
            dvm.save()

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        retry_transaction(call)
        aud.info('Reboot', user_id=user_id, vm_id=vm_id)


@app.task
def destroy_vm(vm_id, user_id=None):
    def call():
        with transaction.atomic():
            dvm = VM.objects.get(id=vm_id).dummyvm
            if dvm.destroyed:
                aud.error(('Can\'t destroy DummyVM {0.id} ‘{0.name}’ with ' +
                    'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
                    ).format(dvm), user_id=user_id, vm_id=vm_id)
                return
            dvm.poweredon = False
            dvm.destroyed = True
            dvm.save()

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        retry_transaction(call)
        aud.info('Destroy', user_id=user_id, vm_id=vm_id)


@app.task
def update_vm_status(vm_id):
    def call():
        """
        Returns the fields destroyed, poweredon from the model.
        """
        with transaction.atomic():
            dvm = VM.objects.get(id=vm_id).dummyvm
            if dvm.destroyed:
                new_status = 'destroyed'
            else:
                new_status = 'powered ' + ('on' if dvm.poweredon else 'off')
            dvm.status = new_status
            dvm.save()
            aud.debug('Update status ‘{}’'.format(new_status), vm_id=vm_id)
            return dvm.destroyed, dvm.poweredon

    with aud.ctx_mgr(vm_id=vm_id):
        destroyed, poweredon = retry_transaction(call)
        if destroyed:
            poweredon = False

        vimma.vmutil.power_log(vm_id, poweredon)
        if not destroyed:
            vimma.vmutil.switch_on_off(vm_id, poweredon)
