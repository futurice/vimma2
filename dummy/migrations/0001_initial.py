# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DummyProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('type', models.CharField(choices=[('dummy', 'Dummy'), ('aws', 'Amazon Web Services')], max_length=20)),
                ('max_override_seconds', models.BigIntegerField(default=0)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DummyVM',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('sched_override_state', models.NullBooleanField(default=None)),
                ('sched_override_tstamp', models.BigIntegerField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.CharField(max_length=200, blank=True)),
                ('status_updated_at', models.DateTimeField(null=True, blank=True)),
                ('destroy_request_at', models.DateTimeField(null=True, blank=True)),
                ('destroyed_at', models.DateTimeField(null=True, blank=True)),
                ('name', models.CharField(max_length=50)),
                ('status', models.CharField(max_length=50, blank=True)),
                ('destroyed', models.BooleanField(default=False)),
                ('poweredon', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='DummyVMConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
