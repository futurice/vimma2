from __future__ import absolute_import

import os
import time

from celery import Celery
from celery.utils.log import get_task_logger

#from celery import shared_task
from django.conf import settings

from vmm.models import VirtualMachine

import aws.AWS_conn

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vimma2.settings')

app = Celery('tasks')
app.config_from_object('django.conf:settings')
logger = get_task_logger(__name__)

@app.task
def create_vm():
    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    vm_name = "demovm" + str(int(time.time()))
    vm_obj = VirtualMachine(primary_name = vm_name, schedule_id = 1)
    vm_obj.save()

    try:
        vm_dict = aws_conn.create_instance(instance_name=vm_name).__dict__
    except:
        VirtualMachine.objects.filter(primary_name=vm_name).delete()
        return dict()
    else:
        setattr(vm_obj, 'instance_id', vm_dict['id'])
        setattr(vm_obj, 'status', 'launched')
        vm_obj.save()
        return vm_dict

@app.task
def terminate_vm(instance_id):
    logger.warning('Terminating instance id: %r' % instance_id)
    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    try:
        aws_conn.terminate_instance(instance_id=instance_id)
        VirtualMachine.objects.filter(instance_id=instance_id).delete()
    except:
        return False
    else:
        return True
