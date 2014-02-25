from django.shortcuts import render
from django.views.generic import TemplateView
from django.http import HttpResponse

from vmm.models import VirtualMachine

# Celery tasks
import tasks

# Vimma 2 main views

def index(request):
    vm_list = VirtualMachine.objects.order_by('-creation_date')
    
    c = {
     'virtual_machines' : vm_list
    }
    
    #result = '<br \> '.join([vm.primary_name for vm in vm_list])
    return render(request, template_name='common/index.html', dictionary=c)

def detail(request, primary_name=None):
    vm = VirtualMachine.objects.get(primary_name=primary_name)
    
    c = {
     'virtual_machines' : [vm]
    }
    return render(request, template_name='common/detail.html', dictionary=c)

def create(request, virtualmachine_id=None):
    task_result = tasks.create_vm.delay()

    result = ""

    while not task_result.ready():
        result += "Waiting for task to complete ..."

    result += "<br />"
    
    result += "task_result.result: %s <br />" % task_result.result
    return HttpResponse(result)

def terminate(request, instance_id):
    result = ""
    task_result = tasks.terminate_vm.delay(instance_id)

    while not task_result.ready():
        result += "Waiting for task to complete ..."

    result += "<br />"
    
    result += "task_result.result: %s <br />" % task_result.result
    return HttpResponse(result)
