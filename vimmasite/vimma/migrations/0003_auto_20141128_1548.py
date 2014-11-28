# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0002_awsvmconfig_region'),
    ]

    operations = [
        migrations.AddField(
            model_name='provider',
            name='default',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
        migrations.AddField(
            model_name='vmconfig',
            name='default',
            field=models.BooleanField(default=False),
            preserve_default=True,
        ),
    ]
