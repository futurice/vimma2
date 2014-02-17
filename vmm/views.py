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
    return render(request, template_name='common/index.html', dictionary=c)

def create(request, virtualmachine_id=None):
    cresult = tasks.add.delay("abc", virtualmachine_id)

    result = "Cresult: %s<br />" % cresult
    
    while not cresult.ready():
        result += "Waiting for task to complete ..."

    result += "<br />"
    
    result += "Cresult.result: %s <br />" % cresult.result 
    return HttpResponse(result)
