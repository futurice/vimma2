# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0009_auto_20150126_1857'),
    ]

    operations = [
        migrations.AlterField(
            model_name='project',
            name='email',
            field=models.EmailField(max_length=254),
        ),
    ]
