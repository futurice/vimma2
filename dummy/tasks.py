from vimma.celery import app

from dummy.models import VM

@app.task
def power_on_vm(vm_id, user_id=None):
    vm = VM.objects.get(id=vm_id)
    vm.auditor.info('Power ON', user_id=user_id)
    if vm.destroyed or vm.poweredon:
        vm.auditor.error(('Can\'t power on VM {vm.id} ‘{vm.name}’ with ' +
            'poweredon ‘{vm.poweredon}’, destroyed ‘{vm.destroyed}’'
            ).format(vm=vm), user_id=user_id)
        return
    vm.poweredon = True
    vm.save()

@app.task
def power_off_vm(vm_id, user_id=None):
    vm = VM.objects.get(id=vm_id)
    vm.auditor.info('Power OFF', user_id=user_id)
    if vm.destroyed or not vm.poweredon:
        vm.auditor.error(('Can\'t power off VM {vm.id} ‘{vm.name}’ with ' +
            'poweredon ‘{vm.poweredon}’, destroyed ‘{vm.destroyed}’'
            ).format(vm=vm), user_id=user_id)
        return
    vm.poweredon = False
    vm.save()

@app.task
def reboot_vm(vm_id, user_id=None):
    vm = VM.objects.get(id=vm_id)
    vm.auditor.info('Reboot', user_id=user_id)
    if vm.destroyed:
        vm.auditor.error(('Can\'t reboot VM {vm.id} ‘{vm.name}’ with ' +
            'poweredon ‘{vm.poweredon}’, destroyed ‘{vm.destroyed}’'
            ).format(vm=vm), user_id=user_id)
        return
    vm.poweredon = True
    vm.save()

@app.task
def destroy_vm(vm_id, user_id=None):
    vm = VM.objects.get(id=vm_id)
    vm.auditor.info('Destroy', user_id=user_id)
    if vm.destroyed:
        vm.auditor.error(('Can\'t destroy VM {vm.id} ‘{vm.name}’ with ' +
            'poweredon ‘{vm.poweredon}’, destroyed ‘{vm.destroyed}’'
            ).format(vm=vm), user_id=user_id)
        return
    vm.poweredon = False
    vm.destroyed = True
    vm.destroyed_at = datetime.datetime.utcnow().replace(tzinfo=utc)
    vm.save()

@app.task
def update_vm_status(vm_id):
    vm = VM.objects.get(id=vm_id)
    if vm.destroyed:
        new_status = 'destroyed'
    else:
        new_status = 'powered ' + ('on' if vm.poweredon else 'off')
    vm.status = new_status
    vm.save()

    vm.auditor.debug('Update status ‘{}’'.format(new_status))

    poweredon = False if vm.destroyed else True

    vm.controller().set_vm_status_updated_at_now()

    vm.controller().power_log(poweredon)
    if not vm.destroyed:
        vm.controller().switch_on_off(vm.poweredon)
