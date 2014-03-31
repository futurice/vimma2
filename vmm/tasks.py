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

@app.task(name = 'enforce-schedules')
def enforce_schedules():
    """ This tasks goes through the local DB and turns VMs off and on as needed. """
    # FIXME: We can make poweron and poweroff much more effective by giving
    # a list of instance ids to start up and down. That'll need to be done.
    import datetime
    import pytz

    logger.debug("Running enforce schedules")
    vm_list = VirtualMachine.objects.all()
    time_now = datetime.datetime.now(pytz.timezone(TIME_ZONE))

    for vm in vm_list:
        if vm.persisting():
            logger.info("VM '%s' has persist_until in the future ('%s'), not enforcing schedules" % (vm.instance_id, vm.persist_until))
            continue
        if vm.status == "running" and not vm.schedule.is_active():
            logger.info("Enforce schedules shutting down VM '%s'" % vm.instance_id)
            poweroff_vm(vm.instance_id)
            continue
        if vm.status == "stopped" and vm.schedule.is_active():
            logger.info("Enforce schedules starting up VM '%s'" % vm.instance_id)
            poweron_vm(vm.instance_id)


@app.task(name = 'refresh-local-state')
def refresh_local_state(instance_id = None):
    """ Refresh the status data from AWS to our local DB. """
    # Let's fetch our local db values
    if not instance_id:
        vm_list = VirtualMachine.objects.all()
    else:
        try:
            vm_list = [ VirtualMachine.objects.get(instance_id=instance_id) ]
        except ObjectDoesNotExist:
            result = "Refresh : No such instance: %s" % instance_id
            return HttpResponse(result)

    # Note: Empty local VM list is a valid scenario.

    # Let's get the remote data from AWS
    #import aws.AWS_conn

    aws_instanceid_to_status_map = {}
    local_instanceid_to_status_map = {}
    # fairly large instanceid to instancedata mapping
    aws_instancedata = {}

    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    all_instances = aws_conn.describe_all_instances()

    logger.info("AWS instance listing.")
    for i, instance in enumerate(all_instances):
        logger.debug("Instance #%d: %s<br />" % (i, instance.__dict__))
        # Let's create our aws_instance_to_status -mapping
        if instance.id and \
           instance.tags and 'VimmaSpawned' in instance.tags.keys() and \
           instance.state not in ('terminated'):
            aws_instanceid_to_status_map[instance.id] = instance.state
            aws_instancedata[instance.id] = instance

    logger.info("Local instance listing.")
    for i, vm in enumerate(vm_list):
        logger.debug("Local instance #%d: %s" % (i, vm.__dict__))
        if vm.instance_id:
            local_instanceid_to_status_map[vm.instance_id] = vm.status

    logger.info("AWS instanceid to state mapping: %r" % aws_instanceid_to_status_map)
    logger.info("Local instanceid to state mapping: %r" % local_instanceid_to_status_map)

    # Let's first do a quick check, comparing the two dicts we made.
    # If they are indentical we have no need for further checks.
    import dictdiffer

    statediff = dictdiffer.DictDiffer(aws_instanceid_to_status_map, \
                                      local_instanceid_to_status_map)

    logger.info("Changed : %r, Added : %r, Removed : %r, Unchanged : %r" % \
        (statediff.changed(), statediff.added(), statediff.removed(), statediff.unchanged()))

    if not (statediff.changed() or statediff.added() or statediff.removed()):
        logger.info("No differences between AWS and local db. Exiting.")
        return

    for changed_item in statediff.changed():
        logger.info("Applying changed status to instance %s" % changed_item)
        vm_obj = VirtualMachine.objects.get(instance_id=changed_item)
        setattr(vm_obj, 'status', aws_instanceid_to_status_map[changed_item])
        vm_obj.save()

    for removed_item in statediff.removed():
        logger.info("Removing local instance %s, it is no longer in AWS." % removed_item)
        VirtualMachine.objects.get(instance_id=removed_item).delete()

    # WARNING: FIXME: We don't know the schedule yet - using hardcoded pk=1!
    for added_item in statediff.added():
        logger.info("Handling addition, instance %s" % added_item)
        if not 'Name' in aws_instancedata[added_item].tags or not aws_instancedata[added_item].tags['Name']:
            logger.warning("no Name tag in instance to be added: %s" % added_item)
            continue

        new_item_name = aws_instancedata[added_item].tags['Name']
        new_item_schedule_pk = 1
        new_item_state = aws_instancedata[added_item].state

        vm_obj = VirtualMachine(primary_name = new_item_name, \
                                schedule_id = new_item_schedule_pk, \
                                status = new_item_state)
        setattr(vm_obj, 'instance_id', aws_instancedata[added_item].id)
        vm_obj.save()
