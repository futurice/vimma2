# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0013_auto_20150526_1125'),
    ]

    operations = [
        migrations.AddField(
            model_name='awsvm',
            name='private_ip_address',
            field=models.CharField(max_length=50, blank=True),
        ),
    ]
