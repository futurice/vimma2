import json, os
import django
django.setup()

from vimma.models import (TimeZone, Schedule, Role, Permission, Project,
    User, Provider, Config,)
import aws.models
import dummy.models

from vimma.perms import Perms, ALL_PERMS
from vimma.util import create_vimma_user

for perm in ALL_PERMS:
    p,_ = Permission.objects.get_or_create(name=perm)

admin_user = create_vimma_user(username=os.getenv('ADMIN_USER', 'admin'),
        email=os.getenv('ADMIN_EMAIL'),
        password=os.getenv('ADMIN_PASS'),
        first_name='Admin',
        last_name='User',)
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.save()

demo_project,_ = Project.objects.get_or_create(name='Demo Project', email='demo@example.com')
admin_user.projects.add(demo_project)

admin_role,_ = Role.objects.get_or_create(name='Administrator')
admin_role.permissions.add(Permission.objects.get(name=Perms.OMNIPOTENT))
admin_user.roles.add(admin_role)

tz_hki,_ = TimeZone.objects.get_or_create(name='Europe/Helsinki')
tz_lon,_ = TimeZone.objects.get_or_create(name='Europe/London')
tz_ger,_ = TimeZone.objects.get_or_create(name='Europe/Germany')

saon,_ = Schedule.objects.get_or_create(name='Always On', timezone=tz_hki,
        matrix=json.dumps(7*[48*[True]]), is_special=True,)
sbiz,_ = Schedule.objects.get_or_create(name='8-17', timezone=tz_hki,
        matrix=json.dumps(7*[10*2*[False] + 8*2*[True] + 6*2*[False]]),)

# DUMMY
dummyprov,_ = dummy.models.Provider.objects.get_or_create(name='My Provider',
        max_override_seconds=60*60)
vmc1A,_ = dummy.models.Config.objects.get_or_create(provider=dummyprov, name='Config A',
        default_schedule=saon)
vmc1B,_ = dummy.models.Config.objects.get_or_create(provider=dummyprov, name='Config B',
        default_schedule=saon, is_special=True)

# 
awsprov,_ = aws.models.Provider.objects.get_or_create(
        name='My Provider', max_override_seconds=60*60,
        access_key_id='AWS_ACCESS_KEY_ID',
        access_key_secret='AWS_ACCESS_KEY_SECRET',
        ssh_key_name=os.getenv('AWS_SSH_KEY_NAME'),
        route_53_zone=os.getenv('AWS_ROUTE_53_NAME'),
        default_security_group_id=os.getenv('AWS_DEFAULT_SECURITY_GROUP_ID'),
        vpc_id=os.getenv('AWS_VPC_ID'),)
vmc3A,_ = aws.models.Config.objects.get_or_create(provider=awsprov,
        ami_id='ami-748e2903', instance_type='t2.micro', region='eu-west-1',
        name=' t2.micro', root_device_size=8, root_device_volume_type='standard',
        default_schedule=saon)