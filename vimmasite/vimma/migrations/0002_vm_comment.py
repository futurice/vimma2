# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='vm',
            name='comment',
            field=models.CharField(max_length=200, default='', blank=True),
            preserve_default=False,
        ),
    ]
