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

def create_cname(vm_name, public_dns_name):
    route53_conn = aws.AWS_conn.Route53Conn()
    route53_conn.connect()
    logger.warning
    route53_conn.create_cname(vm_name, public_dns_name)

@app.task
def create_vm(vm_name):
    logger.warning('Starting to create instance.')
    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    logger.warning('Creating instance with name: %r' % vm_name)

    try:
        vm_dict = aws_conn.create_instance(instance_name=vm_name).__dict__
    except:
        logger.info('Instance creation failed for instance name: %r' % vm_name)
        VirtualMachine.objects.filter(primary_name=vm_name).delete()
        return dict()
    else:
        vm_obj = VirtualMachine.objects.get(primary_name=vm_name)
        setattr(vm_obj, 'instance_id', vm_dict['id'])
        setattr(vm_obj, 'status', 'running')
        vm_obj.save()

        # Create CNAME to Route53
        # WARNING: NOTICE: Perhaps move to own task?
        create_cname(vm_name, vm_dict['dns_name'])
        logger.info("VM creation result dict: %r" % vm_dict)
        return vm_dict

@app.task
def terminate_vm(instance_id):
    logger.info('Terminating instance id: %r' % instance_id)
    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    instance_dict = aws_conn.describe_instance(instance_id).__dict__
    (vm_name, public_dns_name) = (instance_dict['tags']['Name'], instance_dict['public_dns_name'])

    try:
        route53_conn = aws.AWS_conn.Route53Conn()
        route53_conn.connect()
        route53_conn.remove_cname(vm_name, public_dns_name)
    except: # DNSServerError
        logger.error("Failure deleting DNS CNAME record: %s - %s" % (vm_name, public_dns_name))
    else:
        logger.info("Deleted DNS CNAME record: %s - %s" % (vm_name, public_dns_name))

    try:
        aws_conn.terminate_instance(instance_id=instance_id)
    except:
        logger.warning('Instance termination failed for instance id: %r' % instance_id)
        return False
    else:
        VirtualMachine.objects.get(instance_id=instance_id).delete()
        return True

@app.task
def poweroff_vm(instance_id):
    logger.info('Powering off instance id: %r' % instance_id)
    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    instance_dict = aws_conn.describe_instance(instance_id).__dict__
    (vm_name, public_dns_name) = (instance_dict['tags']['Name'], instance_dict['public_dns_name'])

    try:
        route53_conn = aws.AWS_conn.Route53Conn()
        route53_conn.connect()
        route53_conn.remove_cname(vm_name, public_dns_name)
    except: # DNSServerError
        logger.error("Failure deleting DNS CNAME record: %s - %s" % (vm_name, public_dns_name))
    else:
        logger.info("Deleted DNS CNAME record: %s - %s" % (vm_name, public_dns_name))

    try:
        aws_conn.poweroff_instance(instance_id=instance_id)
    except:
        logger.warning('Instance termination failed for instance id: %r' % instance_id)
        return False
    else:
        # Wait for the machine to be properly shut down
        instance = aws_conn.describe_instance(instance_id)

        while instance.state != 'stopped':
            time.sleep(5)
            instance.update()
            print "Instance state: %s" % (instance.state)

        logger.info("Powered off instance: %s - %s" % (instance_id, vm_name))
        vm_obj = VirtualMachine.objects.get(primary_name=vm_name)
        setattr(vm_obj, 'status', 'stopped')
        vm_obj.save()
        return True

@app.task
def poweron_vm(instance_id):
    logger.info('Powering on instance id: %r' % instance_id)
    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    try:
        vm_dict = aws_conn.poweron_instance(instance_id=instance_id).__dict__
    except: # EC2ResponseError
        logger.info('Instance poweron failed for instance: %r' % instance_id)
    else:
        vm_obj = VirtualMachine.objects.get(instance_id=instance_id)
        setattr(vm_obj, 'status', 'running')
        vm_obj.save()

        # Create CNAME to Route53
        # WARNING: NOTICE: Perhaps move to own task?
        create_cname(vm_obj.primary_name, vm_dict['dns_name'])
        logger.info("Power on result dict: %r" % vm_dict)
