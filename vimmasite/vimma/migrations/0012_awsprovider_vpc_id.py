# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0011_auto_20150507_1138'),
    ]

    operations = [
        migrations.AddField(
            model_name='awsprovider',
            name='vpc_id',
            field=models.CharField(max_length=50, default='FIXME'),
            preserve_default=False,
        ),
    ]
