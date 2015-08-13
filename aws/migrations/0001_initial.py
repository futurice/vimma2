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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('ip_protocol', models.CharField(max_length=10, choices=[('tcp', 'TCP'), ('udp', 'UDP')])),
                ('from_port', models.PositiveIntegerField()),
                ('to_port', models.PositiveIntegerField()),
                ('cidr_ip', models.CharField(max_length=50)),
            ],
        ),
        migrations.CreateModel(
            name='AWSProvider',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
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
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
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
        ),
        migrations.CreateModel(
            name='AWSVMConfig',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('region', models.CharField(max_length=20, choices=[('ap-northeast-1', 'ap-northeast-1'), ('ap-southeast-1', 'ap-southeast-1'), ('ap-southeast-2', 'ap-southeast-2'), ('cn-north-1', 'cn-north-1'), ('eu-central-1', 'eu-central-1'), ('eu-west-1', 'eu-west-1'), ('sa-east-1', 'sa-east-1'), ('us-east-1', 'us-east-1'), ('us-gov-west-1', 'us-gov-west-1'), ('us-west-1us-west-2', 'us-west-1us-west-2')])),
                ('ami_id', models.CharField(max_length=50, blank=True)),
                ('instance_type', models.CharField(max_length=50, blank=True)),
                ('root_device_size', models.IntegerField()),
                ('root_device_volume_type', models.CharField(max_length=20, default='standard', choices=[('standard', 'Magnetic'), ('gp2', 'SSD')])),
            ],
        ),
    ]
