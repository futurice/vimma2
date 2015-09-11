from vimma.celery import app

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
