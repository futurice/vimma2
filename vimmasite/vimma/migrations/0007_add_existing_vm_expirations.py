# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import datetime
from django.db import models, migrations
from django.utils.timezone import utc


def add_existing_vm_expirations(apps, schema_editor):
    VM = apps.get_model('vimma', 'VM')
    Expiration = apps.get_model('vimma', 'Expiration')
    VMExpiration = apps.get_model('vimma', 'VMExpiration')
    for vm in VM.objects.all():
        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        exp_dt = now + datetime.timedelta(seconds=60*60*24*30*3)
        exp = Expiration.objects.create(expires_at=exp_dt)
        exp.full_clean()
        VMExpiration.objects.create(expiration=exp, vm=vm).full_clean()


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0006_expiration_vmexpiration'),
    ]

    operations = [
        migrations.RunPython(add_existing_vm_expirations),
    ]
