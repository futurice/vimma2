# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.auth.models
from django.conf import settings
import django.utils.timezone
import django.db.models.deletion
import django.core.validators
import vimma.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('password', models.CharField(verbose_name='password', null=True, max_length=128, blank=True)),
                ('last_login', models.DateTimeField(verbose_name='last login', null=True, blank=True)),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(verbose_name='username', max_length=30, error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', unique=True, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')])),
                ('first_name', models.CharField(verbose_name='first name', max_length=30, blank=True)),
                ('last_name', models.CharField(verbose_name='last name', max_length=30, blank=True)),
                ('email', models.EmailField(verbose_name='email address', max_length=254, blank=True)),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(to='auth.Group', verbose_name='groups', blank=True, related_query_name='user', related_name='user_set', help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.')),
            ],
            options={
                'verbose_name': 'user',
                'abstract': False,
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Audit',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('level', models.CharField(max_length=20, choices=[('1-DEBUG', 'DEBUG'), ('2-INFO', 'INFO'), ('3-WARNING', 'WARNING'), ('4-ERROR', 'ERROR')])),
                ('text', models.CharField(max_length=4096)),
                ('user', models.ForeignKey(to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL, blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='AWSFirewallRule',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('ip_protocol', models.CharField(max_length=10, choices=[('tcp', 'TCP'), ('udp', 'UDP')])),
                ('from_port', models.PositiveIntegerField()),
                ('to_port', models.PositiveIntegerField()),
                ('cidr_ip', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='AWSProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('access_key_id', models.CharField(max_length=100, blank=True)),
                ('access_key_secret', models.CharField(max_length=100, blank=True)),
                ('ssh_key_name', models.CharField(max_length=50, blank=True)),
                ('route_53_zone', models.CharField(max_length=100, blank=True)),
                ('default_security_group_id', models.CharField(max_length=50, blank=True)),
                ('vpc_id', models.CharField(max_length=50)),
                ('user_data', models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='AWSVM',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('state', models.CharField(max_length=100, blank=True)),
                ('name', models.CharField(max_length=50, validators=[vimma.models.aws_vm_name_validator])),
                ('region', models.CharField(max_length=20)),
                ('security_group_id', models.CharField(max_length=50, blank=True)),
                ('reservation_id', models.CharField(max_length=50, blank=True)),
                ('instance_id', models.CharField(max_length=50, blank=True)),
                ('ip_address', models.CharField(max_length=50, blank=True)),
                ('private_ip_address', models.CharField(max_length=50, blank=True)),
                ('instance_terminated', models.BooleanField(default=False)),
                ('security_group_deleted', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='AWSVMConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('region', models.CharField(max_length=20, choices=[('ap-northeast-1', 'ap-northeast-1'), ('ap-southeast-1', 'ap-southeast-1'), ('ap-southeast-2', 'ap-southeast-2'), ('cn-north-1', 'cn-north-1'), ('eu-central-1', 'eu-central-1'), ('eu-west-1', 'eu-west-1'), ('sa-east-1', 'sa-east-1'), ('us-east-1', 'us-east-1'), ('us-gov-west-1', 'us-gov-west-1'), ('us-west-1us-west-2', 'us-west-1us-west-2')])),
                ('ami_id', models.CharField(max_length=50, blank=True)),
                ('instance_type', models.CharField(max_length=50, blank=True)),
                ('root_device_size', models.IntegerField()),
                ('root_device_volume_type', models.CharField(default='standard', max_length=20, choices=[('standard', 'Magnetic'), ('gp2', 'SSD')])),
            ],
        ),
        migrations.CreateModel(
            name='DummyProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='DummyVM',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=50, blank=True)),
                ('destroyed', models.BooleanField(default=False)),
                ('poweredon', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='DummyVMConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='Expiration',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('type', models.CharField(max_length=50, choices=[('vm', 'VM'), ('firewall-rule', 'Firewall Rule')])),
                ('expires_at', models.DateTimeField()),
                ('last_notification', models.DateTimeField(null=True, blank=True)),
                ('grace_end_action_performed', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='FirewallRule',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
            ],
        ),
        migrations.CreateModel(
            name='FirewallRuleExpiration',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('expiration', models.OneToOneField(to='vimma.Expiration')),
                ('firewallrule', models.OneToOneField(to='vimma.FirewallRule')),
            ],
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='PowerLog',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('powered_on', models.BooleanField(default=None)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('type', models.CharField(max_length=20, choices=[('dummy', 'Dummy'), ('aws', 'Amazon Web Services')])),
                ('max_override_seconds', models.BigIntegerField(default=0)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('permissions', models.ManyToManyField(to='vimma.Permission')),
            ],
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('matrix', models.TextField(validators=[vimma.models.schedule_matrix_validator])),
                ('is_special', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='TimeZone',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='VM',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('sched_override_state', models.NullBooleanField(default=None)),
                ('sched_override_tstamp', models.BigIntegerField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.CharField(max_length=200, blank=True)),
                ('status_updated_at', models.DateTimeField(null=True, blank=True)),
                ('destroy_request_at', models.DateTimeField(null=True, blank=True)),
                ('destroyed_at', models.DateTimeField(null=True, blank=True)),
                ('created_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='created_vms', on_delete=django.db.models.deletion.SET_NULL, blank=True, null=True)),
                ('destroy_request_by', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='destroy_requested_vms', on_delete=django.db.models.deletion.SET_NULL, blank=True, null=True)),
                ('project', models.ForeignKey(to='vimma.Project', on_delete=django.db.models.deletion.PROTECT)),
                ('provider', models.ForeignKey(to='vimma.Provider', on_delete=django.db.models.deletion.PROTECT)),
                ('schedule', models.ForeignKey(to='vimma.Schedule', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='VMConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
                ('default_schedule', models.ForeignKey(to='vimma.Schedule', on_delete=django.db.models.deletion.PROTECT)),
                ('provider', models.ForeignKey(to='vimma.Provider', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='VMExpiration',
            fields=[
                ('id', models.AutoField(auto_created=True, verbose_name='ID', serialize=False, primary_key=True)),
                ('expiration', models.OneToOneField(to='vimma.Expiration')),
                ('vm', models.OneToOneField(to='vimma.VM')),
            ],
        ),
        migrations.AddField(
            model_name='schedule',
            name='timezone',
            field=models.ForeignKey(to='vimma.TimeZone', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='powerlog',
            name='vm',
            field=models.ForeignKey(to='vimma.VM'),
        ),
        migrations.AddField(
            model_name='firewallrule',
            name='vm',
            field=models.ForeignKey(to='vimma.VM'),
        ),
        migrations.AddField(
            model_name='dummyvmconfig',
            name='vmconfig',
            field=models.OneToOneField(to='vimma.VMConfig', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='dummyvm',
            name='vm',
            field=models.OneToOneField(to='vimma.VM', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='dummyprovider',
            name='provider',
            field=models.OneToOneField(to='vimma.Provider', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='awsvmconfig',
            name='vmconfig',
            field=models.OneToOneField(to='vimma.VMConfig', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='awsvm',
            name='vm',
            field=models.OneToOneField(to='vimma.VM', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='awsprovider',
            name='provider',
            field=models.OneToOneField(to='vimma.Provider', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='awsfirewallrule',
            name='firewallrule',
            field=models.OneToOneField(to='vimma.FirewallRule'),
        ),
        migrations.AddField(
            model_name='audit',
            name='vm',
            field=models.ForeignKey(to='vimma.VM', on_delete=django.db.models.deletion.SET_NULL, blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='projects',
            field=models.ManyToManyField(to='vimma.Project', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='roles',
            field=models.ManyToManyField(to='vimma.Role', blank=True),
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(to='auth.Permission', verbose_name='user permissions', blank=True, related_query_name='user', related_name='user_set', help_text='Specific permissions for this user.'),
        ),
    ]
