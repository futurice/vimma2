# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0007_add_existing_vm_expirations'),
    ]

    operations = [
        migrations.AddField(
            model_name='expiration',
            name='type',
            field=models.CharField(choices=[('vm', 'VM'), ('firewall-rule', 'Firewall Rule')], max_length=50, default='vm'),
            preserve_default=False,
        ),
    ]
