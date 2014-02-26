import hashlib

from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import HttpResponse
from django.core import serializers

from vmm.models import VirtualMachine

# Celery tasks
import tasks

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
    task_result = tasks.create_vm.delay()

    result = ""

    while not task_result.ready():
        result += "Waiting for task to complete ..."

    result += "<br />"
    
    result += "task_result.result: %s <br />" % task_result.result
    return HttpResponse(result)

def terminate(request, instance_id):
    """ Destroy a virtual machine. """
    result = ""
    task_result = tasks.terminate_vm.delay(instance_id)

    while not task_result.ready():
        result += "Waiting for task to complete ..."

    result += "<br />"
    
    result += "task_result.result: %s <br />" % task_result.result
    return HttpResponse(result)

# Ajax helper views
def vmstatus(request, primary_name=None, format="json"):
    """ Return the JSON data of a virtual machine, or all virtual machines. """
    result = ""
    if request.GET.get('format'):
        format = request.GET.get('format')

    if primary_name == None:
        vm_list = VirtualMachine.objects.order_by('-creation_date')
    else:
        vm_list = [ VirtualMachine.objects.get(primary_name=primary_name) ]

    if format in ("json", "md5"):
        result = serializers.serialize("json", vm_list)
        if format == "md5":
            result = hashlib.md5(result).hexdigest()

    return HttpResponse(result)
