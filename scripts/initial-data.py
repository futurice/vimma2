import django
django.setup()

from vimma.models import (
    TimeZone, Schedule, Role, Permission, Project,
    User, Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,

from vimma.perms import Perms, ALL_PERMS

for perm in ALL_PERMS:
    p,_ = Permission.objects.get_or_create(name=perm)

tz_hki,_ = TimeZone.objects.get_or_create(name='Europe/Helsinki')
s1,_ = Schedule.objects.get_or_create(name='Always On', timezone=tz_hki,
        matrix=json.dumps(7*[48*[True]]), is_special=True,
        )

awsprovider,_ = AWSProvider.objects.get_or_create(provider='AWS',
        defaults=dict(access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            access_key_secret=os.getenv('AWS_ACCESS_KEY_SECRET'),
            ssh_key_name=os.getenv('AWS_SSH_KEY_NAME'),
            route_53_zone=os.getenv('AWS_ROUTE_53_NAME'),
            default_security_group_id=os.getenv('AWS_DEFAULT_SECURITY_GROUP_ID'),
            vpc_id=os.getenv('AWS_VPC_ID')),)

vmc3A,_ = VMConfig.objects.get_or_create(provider=awsprovider, name='Amazon Linux, t2.micro',
        default_schedule=s1)

AWSVMConfig.objects.get_or_create(vmconfig=vmc3A,
        ami_id='ami-748e2903', instance_type='t2.micro', region='eu-west-1',
        root_device_size=8, root_device_volume_type='standard')
