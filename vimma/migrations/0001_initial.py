# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import vimma.models
import django.core.validators
import django.db.models.deletion
import django.contrib.auth.models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(verbose_name='last login', blank=True, null=True)),
                ('is_superuser', models.BooleanField(help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status', default=False)),
                ('username', models.CharField(help_text='Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.', verbose_name='username', unique=True, max_length=30, error_messages={'unique': 'A user with that username already exists.'}, validators=[django.core.validators.RegexValidator('^[\\w.@+-]+$', 'Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.', 'invalid')])),
                ('first_name', models.CharField(max_length=30, verbose_name='first name', blank=True)),
                ('last_name', models.CharField(max_length=30, verbose_name='last name', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='email address', blank=True)),
                ('is_staff', models.BooleanField(help_text='Designates whether the user can log into this admin site.', verbose_name='staff status', default=False)),
                ('is_active', models.BooleanField(help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active', default=True)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('groups', models.ManyToManyField(related_query_name='user', help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', verbose_name='groups', related_name='user_set', to='auth.Group', blank=True)),
            ],
            options={
                'abstract': False,
                'verbose_name': 'user',
                'verbose_name_plural': 'users',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Audit',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('level', models.CharField(max_length=20, choices=[('1-DEBUG', 'DEBUG'), ('2-INFO', 'INFO'), ('3-WARNING', 'WARNING'), ('4-ERROR', 'ERROR')])),
                ('text', models.CharField(max_length=4096)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to=settings.AUTH_USER_MODEL, blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='FirewallRule',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
            ],
        ),
        migrations.CreateModel(
            name='FirewallRuleExpiration',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('expires_at', models.DateTimeField()),
                ('last_notification', models.DateTimeField(blank=True, null=True)),
                ('grace_end_action_performed', models.BooleanField(default=False)),
                ('firewallrule', models.OneToOneField(related_name='expiration', to='vimma.FirewallRule')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Permission',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='PowerLog',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('powered_on', models.BooleanField(default=None)),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('email', models.EmailField(max_length=254)),
            ],
        ),
        migrations.CreateModel(
            name='Provider',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=100)),
                ('permissions', models.ManyToManyField(to='vimma.Permission')),
            ],
        ),
        migrations.CreateModel(
            name='Schedule',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('matrix', models.TextField(validators=[vimma.models.schedule_matrix_validator])),
                ('is_special', models.BooleanField(default=False)),
            ],
        ),
        migrations.CreateModel(
            name='TimeZone',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='VM',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('sched_override_state', models.NullBooleanField(default=None)),
                ('sched_override_tstamp', models.BigIntegerField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.CharField(max_length=200, blank=True)),
                ('status_updated_at', models.DateTimeField(blank=True, null=True)),
                ('destroy_request_at', models.DateTimeField(blank=True, null=True)),
                ('destroyed_at', models.DateTimeField(blank=True, null=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, related_name='created_vms', to=settings.AUTH_USER_MODEL, blank=True)),
                ('destroy_request_by', models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, related_name='destroy_requested_vms', to=settings.AUTH_USER_MODEL, blank=True)),
                ('firewallrules', models.ManyToManyField(to='vimma.FirewallRule', blank=True)),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vimma.Project')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vimma.Provider')),
                ('schedule', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vimma.Schedule')),
            ],
        ),
        migrations.CreateModel(
            name='VMConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
                ('default_schedule', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vimma.Schedule')),
                ('provider', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vimma.Provider')),
            ],
        ),
        migrations.CreateModel(
            name='VMExpiration',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('expires_at', models.DateTimeField()),
                ('last_notification', models.DateTimeField(blank=True, null=True)),
                ('grace_end_action_performed', models.BooleanField(default=False)),
                ('vm', models.OneToOneField(related_name='expiration', to='vimma.VM')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='schedule',
            name='timezone',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='vimma.TimeZone'),
        ),
        migrations.AddField(
            model_name='powerlog',
            name='vm',
            field=models.ForeignKey(to='vimma.VM'),
        ),
        migrations.AddField(
            model_name='audit',
            name='vm',
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, null=True, to='vimma.VM', blank=True),
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
            field=models.ManyToManyField(related_query_name='user', help_text='Specific permissions for this user.', verbose_name='user permissions', related_name='user_set', to='auth.Permission', blank=True),
        ),
    ]
