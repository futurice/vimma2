# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0005_auto_20141229_1220'),
    ]

    operations = [
        migrations.CreateModel(
            name='Expiration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('expires_at', models.DateTimeField()),
                ('last_notification', models.DateTimeField(blank=True, null=True)),
                ('grace_end_action_performed', models.BooleanField(default=False)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VMExpiration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, primary_key=True, auto_created=True)),
                ('expiration', models.OneToOneField(to='vimma.Expiration')),
                ('vm', models.OneToOneField(to='vimma.VM')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
    ]
