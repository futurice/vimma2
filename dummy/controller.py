import datetime
from django.utils.timezone import utc

from vimma.audit import Auditor
from vimma.celery import app
from vimma.util import retry_in_transaction
from vimma.controllers import VMController

from dummy.models import DummyVM, DummyPowerLog

aud = Auditor(__name__)

class DummyVMController(VMController):
    def power_on(self, user_id=None):
        power_on_vm.delay(self.vm.pk, user_id=user_id)

    def power_off(self, user_id=None):
        power_off_vm.delay(self.vm.pk, user_id=user_id)

    def reboot(self, user_id=None):
        reboot_vm.delay(self.vm.pk, user_id=user_id)

    def destroy(self, user_id=None):
        destroy_vm.delay(self.vm.pk, user_id=user_id)

    def update_status(self):
        update_vm_status.delay(self.vm.pk)

    def power_log(self, powered_on):
        DummyPowerLog.objects.create(vm=self.vm, powered_on=powered_on)

    def create_vm_details(self, *args, **kw):
        vm = DummyVM.objects.create(name=kw['name'], config=kw['config'], project=kw['project'], schedule=kw['schedule'])

        delay = 5
        countdown = min(max(0, 5), 60)
        callables = [
                lambda: power_on_vm.apply_async(args=(vm.id, kw['user'].id),
                    countdown=countdown),
                ]
        return vm, callables


@app.task
def power_on_vm(vm_id, user_id=None):
    aud.info('Power ON', user_id=user_id, vm_id=vm_id)
    vm = DummyVM.objects.get(id=vm_id)
    if vm.destroyed or vm.poweredon:
        aud.error(('Can\'t power on DummyVM {0.id} ‘{0.name}’ with ' +
            'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
            ).format(vm), user_id=user_id, vm_id=vm_id)
        return
    vm.poweredon = True
    vm.save()

@app.task
def power_off_vm(vm_id, user_id=None):
    aud.info('Power OFF', user_id=user_id, vm_id=vm_id)
    vm = DummyVM.objects.get(id=vm_id)
    if vm.destroyed or not vm.poweredon:
        aud.error(('Can\'t power off DummyVM {0.id} ‘{0.name}’ with ' +
            'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
            ).format(vm), user_id=user_id, vm_id=vm_id)
        return
    vm.poweredon = False
    vm.save()

@app.task
def reboot_vm(vm_id, user_id=None):
    aud.info('Reboot', user_id=user_id, vm_id=vm_id)
    vm = DummyVM.objects.get(id=vm_id)
    if vm.destroyed:
        aud.error(('Can\'t reboot DummyVM {0.id} ‘{0.name}’ with ' +
            'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
            ).format(vm), user_id=user_id, vm_id=vm_id)
        return
    vm.poweredon = True
    vm.save()

@app.task
def destroy_vm(vm_id, user_id=None):
    aud.info('Destroy', user_id=user_id, vm_id=vm_id)
    vm = DummyVM.objects.get(id=vm_id)
    if vm.destroyed:
        aud.error(('Can\'t destroy DummyVM {0.id} ‘{0.name}’ with ' +
            'poweredon ‘{0.poweredon}’, destroyed ‘{0.destroyed}’'
            ).format(vm), user_id=user_id, vm_id=vm_id)
        return
    vm.poweredon = False
    vm.destroyed = True
    vm.destroyed_at = datetime.datetime.utcnow().replace(tzinfo=utc)
    vm.save()

@app.task
def update_vm_status(vm_id):
    with aud.ctx_mgr(vm_id=vm_id):
        vm = DummyVM.objects.get(id=vm_id)
        if vm.destroyed:
            new_status = 'destroyed'
        else:
            new_status = 'powered ' + ('on' if vm.poweredon else 'off')
        vm.status = new_status
        vm.save()
        aud.debug('Update status ‘{}’'.format(new_status), vm_id=vm_id)

        poweredon = False if vm.destroyed else True

        vm.controller().set_vm_status_updated_at_now()

        vm.controller().power_log(poweredon)
        if not vm.destroyed:
            vm.controller().switch_on_off(vm.poweredon)

