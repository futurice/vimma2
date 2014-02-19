from __future__ import absolute_import

import os

from celery import Celery
from celery import shared_task
from django.conf import settings

import aws.create_ami

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vimma2.settings')

app = Celery('tasks')
app.config_from_object('django.conf:settings')

#@app.task
#def add(x, y):
#    return "celery: "+ x + y

@app.task
def create_vm():
    vm_dict = aws.create_ami.main()
    return vm_dict
