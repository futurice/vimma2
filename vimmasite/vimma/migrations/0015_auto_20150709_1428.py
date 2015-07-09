# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0014_awsvm_private_ip_address'),
    ]

    operations = [
        migrations.AlterField(
            model_name='awsfirewallrule',
            name='ip_protocol',
            field=models.CharField(choices=[('tcp', 'TCP'), ('udp', 'UDP')], max_length=10),
        ),
    ]
