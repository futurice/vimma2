# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import vimma.models
import django.db.models.deletion
from django.conf import settings
import django.core.validators
import django.contrib.auth.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(help_text='Designates that this user has all permissions without explicitly assigning them.', default=False, verbose_name='superuser status')),
                ('username', models.CharField(validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')], max_length=30, error_messages={'unique': 'A user with that username already exists.'}, unique=True, help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', verbose_name='username')),
                ('first_name', models.CharField(max_length=30, blank=True, verbose_name='first name')),
                ('last_name', models.CharField(max_length=30, blank=True, verbose_name='last name')),
                ('email', models.EmailField(max_length=254, blank=True, verbose_name='email address')),
                ('is_staff', models.BooleanField(help_text='Designates whether the user can log into this admin site.', default=False, verbose_name='staff status')),
                ('is_active', models.BooleanField(help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', default=True, verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(related_name='user_set', help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_query_name='user', to='auth.Group', blank=True, verbose_name='groups')),
            ],
            options={
                'abstract': False,
                'verbose_name_plural': 'users',
                'verbose_name': 'user',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Audit',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, auto_now_add=True)),
                ('level', models.CharField(choices=[('1-DEBUG', 'DEBUG'), ('2-INFO', 'INFO'), ('3-WARNING', 'WARNING'), ('4-ERROR', 'ERROR')], max_length=20)),
                ('text', models.CharField(max_length=4096)),
                ('user', models.ForeignKey(blank=True, null=True, to=settings.AUTH_USER_MODEL, on_delete=django.db.models.deletion.SET_NULL)),
            ],
        ),
        migrations.CreateModel(
            name='AWSFirewallRule',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('ip_protocol', models.CharField(choices=[('tcp', 'TCP'), ('udp', 'UDP')], max_length=10)),
                ('from_port', models.PositiveIntegerField()),
                ('to_port', models.PositiveIntegerField()),
                ('cidr_ip', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='AWSProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
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
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('state', models.CharField(max_length=100, blank=True)),
                ('name', models.CharField(validators=[vimma.models.aws_vm_name_validator], max_length=50)),
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
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('region', models.CharField(choices=[('ap-northeast-1', 'ap-northeast-1'), ('ap-southeast-1', 'ap-southeast-1'), ('ap-southeast-2', 'ap-southeast-2'), ('cn-north-1', 'cn-north-1'), ('eu-central-1', 'eu-central-1'), ('eu-west-1', 'eu-west-1'), ('sa-east-1', 'sa-east-1'), ('us-east-1', 'us-east-1'), ('us-gov-west-1', 'us-gov-west-1'), ('us-west-1us-west-2', 'us-west-1us-west-2')], max_length=20)),
                ('ami_id', models.CharField(max_length=50, blank=True)),
                ('instance_type', models.CharField(max_length=50, blank=True)),
                ('root_device_size', models.IntegerField()),
                ('root_device_volume_type', models.CharField(choices=[('standard', 'Magnetic'), ('gp2', 'SSD')], max_length=20, default='standard')),
            ],
        ),
        migrations.CreateModel(
            name='DummyProvider',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='DummyVM',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=50, blank=True)),
                ('destroyed', models.BooleanField(default=False)),
                ('poweredon', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='DummyVMConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='FirewallRule',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
            ],
        ),
        migrations.CreateModel(
            name='FirewallRuleExpiration',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('expires_at', models.DateTimeField()),
                ('last_notification', models.DateTimeField(blank=True, null=True)),
                ('grace_end_action_performed', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='PowerLog',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('timestamp', models.DateTimeField(db_index=True, auto_now_add=True)),
                ('powered_on', models.BooleanField(default=None)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('type', models.CharField(choices=[('dummy', 'Dummy'), ('aws', 'Amazon Web Services')], max_length=20)),
                ('max_override_seconds', models.BigIntegerField(default=0)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('permissions', models.ManyToManyField(to='vimma.Permission')),
            ],
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('matrix', models.TextField(validators=[vimma.models.schedule_matrix_validator])),
                ('is_special', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='TimeZone',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='VM',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('sched_override_state', models.NullBooleanField(default=None)),
                ('sched_override_tstamp', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.CharField(max_length=200, blank=True)),
                ('status_updated_at', models.DateTimeField(blank=True, null=True)),
                ('destroy_request_at', models.DateTimeField(blank=True, null=True)),
                ('destroyed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, to=settings.AUTH_USER_MODEL, related_name='created_vms', on_delete=django.db.models.deletion.SET_NULL)),
                ('destroy_request_by', models.ForeignKey(blank=True, null=True, to=settings.AUTH_USER_MODEL, related_name='destroy_requested_vms', on_delete=django.db.models.deletion.SET_NULL)),
            ],
        ),
        migrations.CreateModel(
            name='VMConfig',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('name', models.CharField(max_length=50, unique=True)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
                ('default_schedule', models.ForeignKey(to='vimma.Schedule', on_delete=django.db.models.deletion.PROTECT)),
                ('provider', models.ForeignKey(to='vimma.Provider', on_delete=django.db.models.deletion.PROTECT)),
            ],
        ),
        migrations.CreateModel(
            name='VMExpiration',
            fields=[
                ('id', models.AutoField(auto_created=True, serialize=False, primary_key=True, verbose_name='ID')),
                ('expires_at', models.DateTimeField()),
                ('last_notification', models.DateTimeField(blank=True, null=True)),
                ('grace_end_action_performed', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='vm',
            name='expiration',
            field=models.ForeignKey(blank=True, null=True, to='vimma.VMExpiration'),
        ),
        migrations.AddField(
            model_name='vm',
            name='project',
            field=models.ForeignKey(to='vimma.Project', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='vm',
            name='provider',
            field=models.ForeignKey(to='vimma.Provider', on_delete=django.db.models.deletion.PROTECT),
        ),
        migrations.AddField(
            model_name='vm',
            name='schedule',
            field=models.ForeignKey(to='vimma.Schedule', on_delete=django.db.models.deletion.PROTECT),
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
            name='expiration',
            field=models.ForeignKey(blank=True, null=True, to='vimma.FirewallRuleExpiration'),
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
            field=models.ForeignKey(blank=True, null=True, to='vimma.VM', on_delete=django.db.models.deletion.SET_NULL),
        ),
        migrations.AddField(
            model_name='user',
            name='projects',
            field=models.ManyToManyField(blank=True, to='vimma.Project'),
        ),
        migrations.AddField(
            model_name='user',
            name='roles',
            field=models.ManyToManyField(blank=True, to='vimma.Role'),
        ),
        migrations.AddField(
            model_name='user',
            name='user_permissions',
            field=models.ManyToManyField(related_name='user_set', help_text='Specific permissions for this user.', related_query_name='user', to='auth.Permission', blank=True, verbose_name='user permissions'),
        ),
    ]
