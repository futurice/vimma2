# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0004_vm_status_updated_at'),
    ]

    operations = [
        migrations.AlterField(
            model_name='powerlog',
            name='timestamp',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
            preserve_default=True,
        ),
    ]
