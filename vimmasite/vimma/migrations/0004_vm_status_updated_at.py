# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0003_auto_20141128_1548'),
    ]

    operations = [
        migrations.AddField(
            model_name='vm',
            name='status_updated_at',
            field=models.DateTimeField(null=True, blank=True),
            preserve_default=True,
        ),
    ]
