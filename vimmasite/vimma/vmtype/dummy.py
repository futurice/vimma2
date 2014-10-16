from django.db import transaction

from vimma.audit import Auditor
from vimma.celery import app
from vimma.models import (
    VM,
    DummyVM,
)
from vimma.util import retry_transaction


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
            lambda: do_power_on_vm.apply_async(args=(vm.id, user_id),
                countdown=countdown),
            ]
    return dummyVM, callables


def power_on_vm(vm_id, data, user_id=None):
    """
    Power on VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.

    The dummy provider's functions try to form a pattern which allows real
    (non-dummy) VM providers reasonable flexibility. This is the purpose
    of the dummy provider.
    This is why these dummy functions have this structure and restrictions
    (e.g. about transactions), even though some of these dummy functions do
    almost no work.
    """
    do_power_on_vm.delay(vm_id=vm_id, user_id=user_id)


@app.task
def do_power_on_vm(vm_id, user_id=None):
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


def power_off_vm(vm_id, data, user_id=None):
    """
    Power off VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.
    """
    do_power_off_vm.delay(vm_id, user_id=user_id)


@app.task
def do_power_off_vm(vm_id, user_id=None):
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


def reboot_vm(vm_id, data, user_id=None):
    """
    Reboot VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.
    """
    do_reboot_vm.delay(vm_id, user_id=user_id)


@app.task
def do_reboot_vm(vm_id, user_id=None):
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


def destroy_vm(vm_id, data, user_id=None):
    """
    Destroy VM.

    ‘data’ is not used.

    This function must not be called inside a transaction.
    """
    do_destroy_vm.delay(vm_id, user_id=user_id)


@app.task
def do_destroy_vm(vm_id, user_id=None):
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
        with transaction.atomic():
            dvm = VM.objects.get(id=vm_id).dummyvm
            if dvm.destroyed:
                new_status = 'destroyed'
            else:
                new_status = 'powered ' + ('on' if dvm.poweredon else 'off')
            dvm.status = new_status
            dvm.save()
        return new_status

    with aud.ctx_mgr(vm_id=vm_id):
        new_status = retry_transaction(call)
        aud.debug('Update status ‘{}’'.format(new_status), vm_id=vm_id)
