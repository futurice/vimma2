# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('vimma', '0010_auto_20150413_1059'),
    ]

    operations = [
        migrations.AlterField(
            model_name='awsvmconfig',
            name='region',
            field=models.CharField(max_length=20, choices=[('ap-northeast-1', 'ap-northeast-1'), ('ap-southeast-1', 'ap-southeast-1'), ('ap-southeast-2', 'ap-southeast-2'), ('cn-north-1', 'cn-north-1'), ('eu-central-1', 'eu-central-1'), ('eu-west-1', 'eu-west-1'), ('sa-east-1', 'sa-east-1'), ('us-east-1', 'us-east-1'), ('us-gov-west-1', 'us-gov-west-1'), ('us-west-1us-west-2', 'us-west-1us-west-2')]),
        ),
    ]
