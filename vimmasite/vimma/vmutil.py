from django.db import transaction

from vimma.models import (
    Provider,
    VM, DummyVM,
)


@transaction.atomic
def create_vm(vmconfig, project, schedule, data):
    """
    Create and return a new VM or throw an exception.

    The data arg is specific to the provider type.
    """
    prov = vmconfig.provider
    vm = VM.objects.create(provider=prov, project=project, schedule=schedule)
    vm.full_clean()
    if prov.type == Provider.TYPE_DUMMY:
        create_dummy_vm(vm, data)
    else:
        raise ValueError('Unknown provider type “{}”'.format(prov.type))
    return vm


def create_dummy_vm(vm, data):
    """
    Create and return a dummy VM, linking to parent ‘vm’, from ‘data’.

    data = {
        name: string,
    }
    """
    dummyVM = DummyVM.objects.create(vm=vm, name=data['name'])
    dummyVM.full_clean()
    return dummyVM
