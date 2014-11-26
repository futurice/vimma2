# https://docs.djangoproject.com/en/1.7/releases/1.7/#standalone-scripts
import django
django.setup()


from django.contrib.auth.models import User

from vimma.util import create_vimma_user
from vimma.models import (
    TimeZone, Schedule, Role, Permission, Project,
    Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
)
from vimma.perms import Perms
import json

import dev_secrets


prj1 = Project.objects.create(name='Demo Prj 1', email='prj1@example.com')
prj2 = Project.objects.create(name='Demo Prj 2', email='prj2@example.com')
# Add all existing users to prj2:
for u in User.objects.all():
    u.profile.projects.add(prj2)


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
r2 = Role.objects.create(name='Demo Role2')
for u2Perm in (
        # comment-out any of these
        Perms.EDIT_SCHEDULE,
        Perms.USE_SPECIAL_SCHEDULE,
        Perms.READ_ANY_PROJECT,
        Perms.USE_SPECIAL_VM_CONFIG,
    ):
    r2.permissions.add(Permission.objects.get(name=u2Perm))

u2.profile.roles.add(r2)

u3 = create_vimma_user('u3', 'u3@example.com', 'pass', 'Colonel', 'Cox')
rOmni = Role.objects.create(name='Demo Role Omnipotent')
pOmni = Permission.objects.get(name=Perms.OMNIPOTENT)
rOmni.permissions.add(pOmni)
u3.profile.roles.add(rOmni)

u1.profile.projects.add(prj1)

u2.profile.projects.add(prj2)

u4 = create_vimma_user('u4', 'u4@example.com', 'pass', 'Dilbert', 'Drape')
u4.profile.projects.add(prj1)


prov1 = Provider.objects.create(name='Dummy Provider',
        type=Provider.TYPE_DUMMY, max_override_seconds=60*60)
DummyProvider.objects.create(provider=prov1)

prov3 = Provider.objects.create(name='AWS Vimma Provider',
        type=Provider.TYPE_AWS, max_override_seconds=60*60)
AWSProvider.objects.create(provider=prov3,
        access_key_id=dev_secrets.AWS_ACCESS_KEY_ID,
        access_key_secret=dev_secrets.AWS_ACCESS_KEY_SECRET,
        ssh_key_name=dev_secrets.AWS_SSH_KEY_NAME,
        route_53_zone=dev_secrets.AWS_ROUTE_53_NAME,
        default_security_group_id=dev_secrets.AWS_DEFAULT_SECURITY_GROUP_ID)


vmc1A = VMConfig.objects.create(provider=prov1, name='Config A',
        default_schedule=s1)
DummyVMConfig.objects.create(vmconfig=vmc1A)
vmc1B = VMConfig.objects.create(provider=prov1, name='Config B',
        default_schedule=s1, is_special=True)
DummyVMConfig.objects.create(vmconfig=vmc1B)

vmc3A = VMConfig.objects.create(provider=prov3, name='Amazon Linux, t2.micro',
        default_schedule=s1)
AWSVMConfig.objects.create(vmconfig=vmc3A,
        ami_id='ami-748e2903', instance_type='t2.micro', region='eu-west-1')
