# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0008_expiration_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='AWSFirewallRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ip_protocol', models.CharField(choices=[('tcp', 'TCP'), ('udp', 'UDP'), ('icmp', 'ICMP')], max_length=10)),
                ('from_port', models.PositiveIntegerField()),
                ('to_port', models.PositiveIntegerField()),
                ('cidr_ip', models.CharField(max_length=50)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FirewallRule',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('vm', models.ForeignKey(to='vimma.VM')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='FirewallRuleExpiration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('expiration', models.OneToOneField(to='vimma.Expiration')),
                ('firewallrule', models.OneToOneField(to='vimma.FirewallRule')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='awsfirewallrule',
            name='firewallrule',
            field=models.OneToOneField(to='vimma.FirewallRule'),
            preserve_default=True,
        ),
    ]
