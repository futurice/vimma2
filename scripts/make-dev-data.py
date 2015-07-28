# https://docs.djangoproject.com/en/1.7/releases/1.7/#standalone-scripts
import django
django.setup()

from vimma.util import create_vimma_user
from vimma.models import (
    TimeZone, Schedule, Role, Permission, Project,
    User, Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
)
from vimma.perms import Perms, ALL_PERMS
import json, os

for perm in ALL_PERMS:
    p,_ = Permission.objects.get_or_create(name=perm)

prj1,_ = Project.objects.get_or_create(name='Demo Prj 1', email='prj1@example.com')
prj2,_ = Project.objects.get_or_create(name='Demo Prj 2', email='prj2@example.com')
# Add all existing users to prj2:
for u in User.objects.all():
    u.projects.add(prj2)

u1 = create_vimma_user('u1', 'u1@example.com', 'pass', 'Andrew', 'Adams')
tz_hki,_ = TimeZone.objects.get_or_create(name='Europe/Helsinki')
TimeZone.objects.get_or_create(name='Europe/London')
TimeZone.objects.get_or_create(name='America/Los_Angeles')
s1,_ = Schedule.objects.get_or_create(name='My Schedule', timezone=tz_hki,
        matrix=json.dumps(7*[10*2*[False] + 8*2*[True] + 6*2*[False]])
        )
s2,_ = Schedule.objects.get_or_create(name='Always On', timezone=tz_hki,
        matrix=json.dumps(7*[48*[True]]), is_special=True,
        )

u2 = create_vimma_user('u2', 'u2@example.com', 'pass', 'Barbie', 'Barbara')
r2,_ = Role.objects.get_or_create(name='Demo Role2')

for u2Perm in (
        # comment-out any of these
        Perms.EDIT_SCHEDULE,
        Perms.USE_SPECIAL_SCHEDULE,
        Perms.READ_ANY_PROJECT,
        Perms.USE_SPECIAL_VM_CONFIG,
    ):
    r2.permissions.add(Permission.objects.get(name=u2Perm))

u2.roles.add(r2)

u3 = create_vimma_user('u3', 'u3@example.com', 'pass', 'Colonel', 'Cox')
rOmni,_ = Role.objects.get_or_create(name='Demo Role Omnipotent')
pOmni = Permission.objects.get(name=Perms.OMNIPOTENT)
rOmni.permissions.add(pOmni)
u3.roles.add(rOmni)

u1.projects.add(prj1)
u2.projects.add(prj2)

u4 = create_vimma_user('u4', 'u4@example.com', 'pass', 'Dilbert', 'Drape')
u4.projects.add(prj1)


# Dummy

prov1,_ = Provider.objects.get_or_create(name='Dummy',
        type=Provider.TYPE_DUMMY, max_override_seconds=60*60)

DummyProvider.objects.get_or_create(provider=prov1)

vmc1A,_ = VMConfig.objects.get_or_create(provider=prov1, name='Config A',
        default_schedule=s1)
DummyVMConfig.objects.get_or_create(vmconfig=vmc1A)
vmc1B,_ = VMConfig.objects.get_or_create(provider=prov1, name='Config B',
        default_schedule=s1, is_special=True)
DummyVMConfig.objects.get_or_create(vmconfig=vmc1B)


# AWS

prov3,_ = Provider.objects.get_or_create(name='AWS Demo',
        type=Provider.TYPE_AWS, max_override_seconds=60*60)
AWSProvider.objects.get_or_create(provider=prov3,
        access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
        access_key_secret=os.getenv('AWS_ACCESS_KEY_SECRET'),
        ssh_key_name=os.getenv('AWS_SSH_KEY_NAME'),
        route_53_zone=os.getenv('AWS_ROUTE_53_NAME'),
        default_security_group_id=os.getenv('AWS_DEFAULT_SECURITY_GROUP_ID'),
        vpc_id=os.getenv('AWS_VPC_ID'),)

vmc3A,_ = VMConfig.objects.get_or_create(provider=prov3, name='Amazon Linux, t2.micro',
        default_schedule=s1)
AWSVMConfig.objects.get_or_create(vmconfig=vmc3A,
        ami_id='ami-748e2903', instance_type='t2.micro', region='eu-west-1',
        root_device_size=8, root_device_volume_type='standard')

vmc3B,_ = VMConfig.objects.get_or_create(provider=prov3,
        name='Futu-Vimma Image, t2.micro', default_schedule=s1, default=True)
AWSVMConfig.objects.get_or_create(vmconfig=vmc3B,
        ami_id='ami-748e2903', instance_type='t2.micro',
        region='eu-west-1',
        root_device_size=12, root_device_volume_type='gp2')
