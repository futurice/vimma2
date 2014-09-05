from vimma.util import create_vimma_user
from vimma.models import (
    TimeZone, Schedule, Role, Permission, Project,
    Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
    VM, DummyVM, AWSVM,
)
from vimma.perms import Perms
import json

u1 = create_vimma_user('u1', 'u1@example.com', 'pass', 'Andrew', 'Adams')
tz_hki = TimeZone.objects.create(name='Europe/Helsinki')
TimeZone.objects.create(name='Europe/London')
TimeZone.objects.create(name='America/Los_Angeles')
s1 = Schedule.objects.create(name='My Schedule', timezone=tz_hki,
        matrix=json.dumps(7*[10*2*[False] + 8*2*[True] + 6*2*[False]])
        )
s1.full_clean()
s2 = Schedule.objects.create(name='Always On', timezone=tz_hki,
        matrix=json.dumps(7*[48*[True]]), is_special=True,
        )
s2.full_clean()

u2 = create_vimma_user('u2', 'u2@example.com', 'pass', 'Barbie', 'Barbara')
r2 = Role.objects.create(name='Role2')
for u2Perm in (
        # comment-out any of these
        Perms.EDIT_SCHEDULE,
        Perms.USE_SPECIAL_SCHEDULE,
        Perms.READ_ANY_PROJECT,
        Perms.VM_CONF_INSTANTIATE,
    ):
    r2.permissions.add(Permission.objects.create(name=u2Perm))

u2.profile.roles.add(r2)

u3 = create_vimma_user('u3', 'u3@example.com', 'pass', 'Colonel', 'Cox')
rOmni = Role.objects.create(name='omnipotent')
pOmni = Permission.objects.create(name=Perms.OMNIPOTENT)
rOmni.permissions.add(pOmni)
u3.profile.roles.add(rOmni)

prj1 = Project.objects.create(name='A Project', email='prj1@example.com')
u1.profile.projects.add(prj1)

prj2 = Project.objects.create(name='Second Project', email='prj2@example.com')
u2.profile.projects.add(prj2)

u4 = create_vimma_user('u4', 'u4@example.com', 'pass', 'Dilbert', 'Drape')
u4.profile.projects.add(prj1)


prov1 = Provider.objects.create(name='My First Dummy Provider',
        type=Provider.TYPE_DUMMY)
DummyProvider.objects.create(provider=prov1)

prov2 = Provider.objects.create(name='My Second Dummy Provider',
        type=Provider.TYPE_DUMMY)
DummyProvider.objects.create(provider=prov2)

prov3 = Provider.objects.create(name='My First AWS Provider',
        type=Provider.TYPE_AWS)
AWSProvider.objects.create(provider=prov3)

prov4 = Provider.objects.create(name='My Second AWS Provider',
        type=Provider.TYPE_AWS)
AWSProvider.objects.create(provider=prov4)


vmc1A = VMConfig.objects.create(provider=prov1, name='Config A',
        default_schedule=s1)
DummyVMConfig.objects.create(vmconfig=vmc1A)
vmc1B = VMConfig.objects.create(provider=prov1, name='Config B',
        default_schedule=s1, requires_permission=True)
DummyVMConfig.objects.create(vmconfig=vmc1B)

vmc2A = VMConfig.objects.create(provider=prov2, name='Config 2A',
        default_schedule=s2)
DummyVMConfig.objects.create(vmconfig=vmc2A)

vmc3A = VMConfig.objects.create(provider=prov3, name='Config 3A',
        default_schedule=s1)
AWSVMConfig.objects.create(vmconfig=vmc3A)
vmc3B = VMConfig.objects.create(provider=prov3, name='Config 3B',
        default_schedule=s2)
AWSVMConfig.objects.create(vmconfig=vmc3B)


vm1 = VM.objects.create(provider=prov1, project=prj1, schedule=s1)
dvm1 = DummyVM.objects.create(vm=vm1, name='K.I.T.T.')
vm2 = VM.objects.create(provider=prov2, project=prj2, schedule=s1)
dvm2 = DummyVM.objects.create(vm=vm2, name='HAL')

vm3 = VM.objects.create(provider=prov3, project=prj1, schedule=s1)
avm3 = AWSVM.objects.create(vm=vm3)
vm4 = VM.objects.create(provider=prov3, project=prj1, schedule=s1)
avm4 = AWSVM.objects.create(vm=vm4)

# newlines at end to ensure everything runs when piping to the python shell
