# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import aws.models


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='AWSFirewallRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('ip_protocol', models.CharField(choices=[('tcp', 'TCP'), ('udp', 'UDP')], max_length=10)),
                ('from_port', models.PositiveIntegerField()),
                ('to_port', models.PositiveIntegerField()),
                ('cidr_ip', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='AWSProvider',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('type', models.CharField(choices=[('dummy', 'Dummy'), ('aws', 'Amazon Web Services')], max_length=20)),
                ('max_override_seconds', models.BigIntegerField(default=0)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
                ('access_key_id', models.CharField(max_length=100, blank=True)),
                ('access_key_secret', models.CharField(max_length=100, blank=True)),
                ('ssh_key_name', models.CharField(max_length=50, blank=True)),
                ('route_53_zone', models.CharField(max_length=100, blank=True)),
                ('default_security_group_id', models.CharField(max_length=50, blank=True)),
                ('vpc_id', models.CharField(max_length=50)),
                ('user_data', models.TextField(blank=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AWSVM',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('sched_override_state', models.NullBooleanField(default=None)),
                ('sched_override_tstamp', models.BigIntegerField(null=True, blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('comment', models.CharField(max_length=200, blank=True)),
                ('status_updated_at', models.DateTimeField(null=True, blank=True)),
                ('destroy_request_at', models.DateTimeField(null=True, blank=True)),
                ('destroyed_at', models.DateTimeField(null=True, blank=True)),
                ('state', models.CharField(max_length=100, blank=True)),
                ('name', models.CharField(max_length=50, validators=[aws.models.aws_vm_name_validator])),
                ('region', models.CharField(max_length=20)),
                ('security_group_id', models.CharField(max_length=50, blank=True)),
                ('reservation_id', models.CharField(max_length=50, blank=True)),
                ('instance_id', models.CharField(max_length=50, blank=True)),
                ('ip_address', models.CharField(max_length=50, blank=True)),
                ('private_ip_address', models.CharField(max_length=50, blank=True)),
                ('instance_terminated', models.BooleanField(default=False)),
                ('security_group_deleted', models.BooleanField(default=False)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='AWSVMConfig',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('name', models.CharField(unique=True, max_length=50)),
                ('is_special', models.BooleanField(default=False)),
                ('default', models.BooleanField(default=False)),
                ('region', models.CharField(choices=[('ap-northeast-1', 'ap-northeast-1'), ('ap-southeast-1', 'ap-southeast-1'), ('ap-southeast-2', 'ap-southeast-2'), ('cn-north-1', 'cn-north-1'), ('eu-central-1', 'eu-central-1'), ('eu-west-1', 'eu-west-1'), ('sa-east-1', 'sa-east-1'), ('us-east-1', 'us-east-1'), ('us-gov-west-1', 'us-gov-west-1'), ('us-west-1us-west-2', 'us-west-1us-west-2')], max_length=20)),
                ('ami_id', models.CharField(max_length=50, blank=True)),
                ('instance_type', models.CharField(max_length=50, blank=True)),
                ('root_device_size', models.IntegerField()),
                ('root_device_volume_type', models.CharField(choices=[('standard', 'Magnetic'), ('gp2', 'SSD')], max_length=20, default='standard')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
