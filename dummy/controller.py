import datetime
from django.utils.timezone import utc

from vimma.audit import Auditor
from vimma.util import retry_in_transaction
from vimma.controllers import VMController

from dummy.models import DummyVM, DummyPowerLog
from dummy.tasks import power_on_vm, power_off_vm, reboot_vm, destroy_vm, update_vm_status

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
        expiration, _ = DummyVMExpiration.objects.get_or_create(vm=vm, expires_at=kw['expires_at'])

        delay = 5
        countdown = min(max(0, 5), 60)
        callables = [
                lambda: power_on_vm.apply_async(args=(vm.id, kw['user'].id),
                    countdown=countdown),
                ]
        return vm, callables

