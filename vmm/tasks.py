from __future__ import absolute_import

import os
import time

from celery import Celery

#from celery import shared_task
from django.conf import settings

from vmm.models import VirtualMachine

import aws.create_ami

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vimma2.settings')

app = Celery('tasks')
app.config_from_object('django.conf:settings')

@app.task
def create_vm():
    vm_name = "demovm" + str(int(time.time()))
    vm_obj = VirtualMachine(primary_name = vm_name, schedule_id = 1)
    vm_obj.save()
    vm_dict = aws.create_ami.main()
    #vm_dict = {}
    return vm_dict
