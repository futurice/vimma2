# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0012_awsprovider_vpc_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='awsvmconfig',
            name='root_device_size',
            field=models.IntegerField(default=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='awsvmconfig',
            name='root_device_volume_type',
            field=models.CharField(max_length=20, choices=[('standard', 'Magnetic'), ('gp2', 'SSD')], default='standard'),
        ),
    ]
