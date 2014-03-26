import hashlib
import time

from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import HttpResponse, HttpResponseRedirect
from django.core import serializers
from django.core.urlresolvers import reverse
from django.core.exceptions import ObjectDoesNotExist

from stronghold.decorators import public

from vmm.models import VirtualMachine

# Celery tasks
import tasks

# http://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-instance-lifecycle.html

# Vimma 2 main views

def index(request):
    """ List all machines """
    vm_list = VirtualMachine.objects.order_by('-creation_date')

    c = {
     'virtual_machines' : vm_list
    }

    #result = '<br \> '.join([vm.primary_name for vm in vm_list])
    return render(request, template_name='common/index.html', dictionary=c)

def detail(request, primary_name=None):
    """ Display info of a specific machine. """
    vm = VirtualMachine.objects.get(primary_name=primary_name)

    c = {
     'virtual_machines' : [vm]
    }
    return render(request, template_name='common/detail.html', dictionary=c)

# Virtual machine creation, termination views

def create(request, virtualmachine_id=None):
    """ Create a new virtual machine. """
    vm_name = "demovm" + str(int(time.time()*100))

    # We synchronously add an entry to our local DB to make
    # sure it is there when returning to the page
    vm_obj = VirtualMachine(primary_name = vm_name, schedule_id = 1, status = 'pending')
    #setattr(vm_obj, 'status', 'pending')
    vm_obj.save()

    task_result = tasks.create_vm.delay(vm_name)

    result = ""
    result += "task_result.result: %s <br />" % task_result.result
    return HttpResponseRedirect("/")

def terminate(request, instance_id):
    """ Destroy a virtual machine. """
    vm_obj = VirtualMachine.objects.get(instance_id=instance_id)
    setattr(vm_obj, 'status', 'shutting-down')
    vm_obj.save()

    task_result = tasks.terminate_vm.delay(instance_id)
    return HttpResponseRedirect("/")

def poweron(request, instance_id):
    """ Poweron / Start up a virtual machine. """
    vm_obj = VirtualMachine.objects.get(instance_id=instance_id)
    setattr(vm_obj, 'status', 'pending')
    vm_obj.save()
    task_result = tasks.poweron_vm.delay(instance_id)
    return HttpResponseRedirect("/")

def poweroff(request, instance_id):
    """ Poweroff / Shutdown a virtual machine. """
    vm_obj = VirtualMachine.objects.get(instance_id=instance_id)
    setattr(vm_obj, 'status', 'stopping')
    vm_obj.save()

    task_result = tasks.poweroff_vm.delay(instance_id)
    return HttpResponseRedirect("/")


# Ajax helper views
def vmstatus(request, primary_name=None, format="json"):
    """ Return the JSON data of a virtual machine, or all virtual machines. """
    result = ""
    if request.GET.get('format'):
        format = request.GET.get('format')

    if primary_name == None:
        vm_list = VirtualMachine.objects.order_by('-creation_date')
    else:
        try:
            vm_list = [ VirtualMachine.objects.get(primary_name=primary_name) ]
        except ObjectDoesNotExist:
            vm_list = []

    if format in ("json", "md5"):
        result = serializers.serialize("json", vm_list)
        if format == "md5" and vm_list:
            result = hashlib.md5(result).hexdigest()

    return HttpResponse(result)

@public
def vmcreatedtime(request, primary_name=None, format="epoch"):
    """ Return the JSON data of a virtual machine, or all virtual machines. """
    result = "0"
    if request.GET.get('format'):
        format = request.GET.get('format')

    if primary_name != None:
        try:
            vm_list = [ VirtualMachine.objects.get(primary_name=primary_name) ]
        except ObjectDoesNotExist:
            vm_list = []

    if format in ("epoch", "iso") and vm_list:
        if format == "iso":
            result = vm_list[0].creation_date
        else:
            result = vm_list[0].creation_date.strftime("%s")

    return HttpResponse(result)

# Background tasks

def refresh_local_state(request, instance_id="all"):
    """
    Refresh the state(s) of one or several instances, updating the local db
    with values from AWS.
    """
    result = ""
    # Let's fetch our local db values
    if instance_id == "all":
        vm_list = VirtualMachine.objects.all()
    else:
        try:
            vm_list = [ VirtualMachine.objects.get(instance_id=instance_id) ]
        except ObjectDoesNotExist:
            result = "Refresh : No such instance: %s" % instance_id
            return HttpResponse(result)

    # Note: Empty local VM list is a valid scenario.

    # Let's get the remote data from AWS
    import aws.AWS_conn

    aws_instanceid_to_status_map = {}
    local_instanceid_to_status_map = {}
    # fairly large instanceid to instancedata mapping
    aws_instancedata = {}

    aws_conn = aws.AWS_conn.EC2Conn()
    aws_conn.connect()

    all_instances = aws_conn.describe_all_instances()

    result += "AWS instance listing:\n<br />"
    for i, instance in enumerate(all_instances):
        result += "Instance #%d: %s<br />" % (i, instance.__dict__)
        # Let's create our aws_instance_to_status -mapping
        if instance.id and \
           instance.tags and 'VimmaSpawned' in instance.tags.keys() and \
           instance.state not in ('terminated'):
            aws_instanceid_to_status_map[instance.id] = instance.state
            aws_instancedata[instance.id] = instance

    result += "Local instance listing:\n<br />"
    for i, vm in enumerate(vm_list):
        result += "Local instance #%d: %s<br />" % (i, vm.__dict__)
        if vm.instance_id:
            local_instanceid_to_status_map[vm.instance_id] = vm.status

    result += "AWS instanceid to state mapping: <br />"
    result += "%r<br />" % aws_instanceid_to_status_map

    result += "Local instanceid to state mapping: <br />"
    result += "%r<br />" % local_instanceid_to_status_map

    # Let's first do a quick check, comparing the two dicts we made.
    # If they are indentical we have no need for further checks.
    import dictdiffer

    statediff = dictdiffer.DictDiffer(aws_instanceid_to_status_map, \
                                      local_instanceid_to_status_map)

    result += "Changed : %r<br />" % statediff.changed()
    result += "Added : %r<br />" % statediff.added()
    result += "Removed : %r<br />" % statediff.removed()
    result += "Unchanged : %r<br />" % statediff.unchanged()

    result += "<hr>"

    if not (statediff.changed() or statediff.added() or statediff.removed()):
        result += "No differences between AWS and local db. Exiting."
        return HttpResponse(result)
    else:
        result += "There are changes."

    for changed_item in statediff.changed():
        print "Entered changed-for"
        result += "Applying changed status to instance %s<br />" % changed_item
        vm_obj = VirtualMachine.objects.get(instance_id=changed_item)
        setattr(vm_obj, 'status', aws_instanceid_to_status_map[changed_item])
        vm_obj.save()

    for removed_item in statediff.removed():
        print "Entered removed-for for item: %r" % removed_item
        result += "Removing local instance %s, it is no longer in AWS<br />" % removed_item
        VirtualMachine.objects.get(instance_id=removed_item).delete()

    # WARNING: FIXME: We don't know the schedule yet - using hardcoded pk=1!
    for added_item in statediff.added():
        print "Handling addition, instance %s" % added_item
        if not 'Name' in aws_instancedata[added_item].tags or not aws_instancedata[added_item].tags['Name']:
            result += "WARNING: no Name tag in instance to be added: %s" % added_item
            continue

        new_item_name = aws_instancedata[added_item].tags['Name']
        new_item_schedule_pk = 1
        new_item_state = aws_instancedata[added_item].state

        vm_obj = VirtualMachine(primary_name = new_item_name, \
                                schedule_id = new_item_schedule_pk, \
                                status = new_item_state)
        setattr(vm_obj, 'instance_id', aws_instancedata[added_item].id)
        vm_obj.save()

    return HttpResponse(result)
