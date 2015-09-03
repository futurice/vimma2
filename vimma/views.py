import datetime
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render
from django.utils.timezone import utc
import json
import pytz
from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)
import sys
import traceback

from vimma import vmutil
from vimma.actions import Actions
from vimma.audit import Auditor
import vimma.expiry
from vimma.models import (
    Schedule, TimeZone, Project,
    User, VM,
    Audit, Expiration, VMExpiration,
    FirewallRule, FirewallRuleExpiration,
)
from dummy.models import DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog
from aws.models import AWSProvider, AWSVMConfig, AWSVM, AWSFirewallRule, AWSAudit, AWSPowerLog

from vimma.util import (
        can_do, login_required_or_forbidden, get_http_json_err,
        retry_in_transaction,
)
from vimmasite.pagination import VimmaPagination


aud = Auditor(__name__)


@login_required_or_forbidden
def index(request):
    return render(request, 'vimma/index.html')

aws_firewall_rule_protocol_choices_json = json.dumps([
    {'value': c[0], 'label': c[1]}
    for c in AWSFirewallRule.IP_PROTOCOL_CHOICES])

@login_required_or_forbidden
def base_js(request):
    """
    base.js, included by the html template(s).
    """
    return render(request, 'vimma/base.js', {
        'pagination': VimmaPagination,
        'audit_level_choices_json': audit_levels_json,
        'aws_firewall_rule_protocol_choices_json':
        aws_firewall_rule_protocol_choices_json,
    }, content_type='application/javascript; charset=utf-8')


# Allow unauthenticated access in order to easily test with browser automation
#@login_required_or_forbidden
def test(request):
    """
    JavaScript Unit Tests.
    """
    return render(request, 'vimma/test.html')


@login_required_or_forbidden
def create_vm(request):
    """
    Create a new VM.

    JSON request body:
    {
        type: string,
        project: int,
        vmconfig: int,
        schedule: int,
        comment: string,
        data: «provider-specific data»,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    body = json.loads(request.read().decode('utf-8'))

    vm = VM.choices()[body['type']]

    try:
        prj = Project.objects.get(id=body['project'])
        vmconf = VMConfig.objects.get(id=body['vmconfig'])
        schedule = Schedule.objects.get(id=body['schedule'])
    except ObjectDoesNotExist as e:
        return get_http_json_err('{}'.format(e), status.HTTP_404_NOT_FOUND)

    if not can_do(request.user, Actions.CREATE_VM_IN_PROJECT, prj):
        return get_http_json_err('You may not create VMs in this project',
                status.HTTP_403_FORBIDDEN)

    if not can_do(request.user, Actions.USE_PROVIDER, vmconf.provider):
        return get_http_json_err('You may not use this provider',
                status.HTTP_403_FORBIDDEN)

    if not can_do(request.user, Actions.USE_VM_CONFIG, vmconf):
        return get_http_json_err('You may not use this VM Configuration',
                status.HTTP_403_FORBIDDEN)

    if vmconf.default_schedule.id != schedule.id:
        if not can_do(request.user, Actions.USE_SCHEDULE, schedule):
            return get_http_json_err('You may not use this schedule',
                    status.HTTP_403_FORBIDDEN)

    if request.META['SERVER_NAME'] == "testserver":
        # Don't create the VMs when running tests
        return HttpResponse()

    vimma.vmutil.create_vm(vmconf, prj, schedule, body['comment'], body['data'],
            request.user.id)
    return HttpResponse()


@login_required_or_forbidden
def power_on_vm(request):
    """
    Power on a VM.

    JSON request body:
    {
        vmid: int,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    body = json.loads(request.read().decode('utf-8'))
    vm_id = body['vmid']
    try:
        vm = VM.objects.get(id=vm_id)
    except ObjectDoesNotExist as e:
        return get_http_json_err('{}'.format(e), status.HTTP_404_NOT_FOUND)

    if not can_do(request.user,
            Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT, vm.project):
        return get_http_json_err('You may not power on VMs in this project',
                status.HTTP_403_FORBIDDEN)
    del vm

    if request.META['SERVER_NAME'] == "testserver":
        # Don't perform the action when running tests
        return HttpResponse()

    try:
        aud.debug('Request to Power ON', vm_id=vm_id, user_id=request.user.id)
        vmutil.get_vm_controller(vm_id).power_on(user_id=request.user.id)
        return HttpResponse()
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id, vm_id=vm_id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def power_off_vm(request):
    """
    Power off a VM.

    JSON request body:
    {
        vmid: int,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    body = json.loads(request.read().decode('utf-8'))
    vm_id = body['vmid']
    try:
        vm = VM.objects.get(id=vm_id)
    except ObjectDoesNotExist as e:
        return get_http_json_err('{}'.format(e), status.HTTP_404_NOT_FOUND)

    if not can_do(request.user,
            Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT, vm.project):
        return get_http_json_err('You may not power off VMs in this project',
                status.HTTP_403_FORBIDDEN)
    del vm

    if request.META['SERVER_NAME'] == "testserver":
        # Don't perform the action when running tests
        return HttpResponse()

    try:
        aud.debug('Request to Power OFF', vm_id=vm_id, user_id=request.user.id)
        vmutil.get_vm_controller(vm_id).power_off(user_id=request.user.id)
        return HttpResponse()
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id, vm_id=vm_id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def reboot_vm(request):
    """
    Reboot a VM.

    JSON request body:
    {
        vmid: int,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    body = json.loads(request.read().decode('utf-8'))
    vm_id = body['vmid']
    try:
        vm = VM.objects.get(id=vm_id)
    except ObjectDoesNotExist as e:
        return get_http_json_err('{}'.format(e), status.HTTP_404_NOT_FOUND)

    if not can_do(request.user,
            Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT, vm.project):
        return get_http_json_err('You may not reboot VMs in this project',
                status.HTTP_403_FORBIDDEN)
    del vm

    if request.META['SERVER_NAME'] == "testserver":
        # Don't perform the action when running tests
        return HttpResponse()

    try:
        aud.debug('Request to Reboot', vm_id=vm_id, user_id=request.user.id)
        vmutil.get_vm_controller(vm_id).reboot(user_id=request.user.id)
        return HttpResponse()
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id, vm_id=vm_id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def destroy_vm(request):
    """
    Destroy a VM.

    JSON request body:
    {
        vmid: int,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    body = json.loads(request.read().decode('utf-8'))
    vm_id = body['vmid']

    def check_err():
        try:
            vm = VM.objects.get(id=vm_id)
        except ObjectDoesNotExist as e:
            return get_http_json_err('{}'.format(e),
                    status.HTTP_404_NOT_FOUND)

        if not can_do(request.user,
                Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT,
                vm.project):
            return get_http_json_err(
                    'You may not destroy VMs in this project',
                    status.HTTP_403_FORBIDDEN)

        now = datetime.datetime.utcnow().replace(tzinfo=utc)
        vm.destroy_request_at = now
        vm.destroy_request_by = request.user
        vm.full_clean()
        vm.save()
    err = retry_in_transaction(check_err)
    if err:
        return err

    if request.META['SERVER_NAME'] == "testserver":
        # Don't perform the action when running tests
        return HttpResponse()

    try:
        aud.debug('Request to Destroy', vm_id=vm_id, user_id=request.user.id)
        vmutil.get_vm_controller(vm_id).destroy(user_id=request.user.id)
        return HttpResponse()
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id, vm_id=vm_id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def override_schedule(request):
    """
    Add or remove a ‘schedule override’ for a VM.

    JSON request body:
    {
        vmid: int,
        state: true | false | null, // for Power ON | Power OFF | no override
        seconds: int,   // duration, starting now; ignored if state is null
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    body = json.loads(request.read().decode('utf-8'))
    try:
        vm = VM.objects.get(id=body['vmid'])
    except ObjectDoesNotExist as e:
        return get_http_json_err('{}'.format(e), status.HTTP_404_NOT_FOUND)

    if not can_do(request.user, Actions.OVERRIDE_VM_SCHEDULE, vm):
        return get_http_json_err('You may not override this vm\'s schedule',
                status.HTTP_403_FORBIDDEN)

    try:
        state = body['state']
        if state is not None:
            seconds = body['seconds']
            max_secs = vm.provider.max_override_seconds
            if seconds > max_secs:
                return get_http_json_err(('{}s is too long, ' +
                    'must be ≤ {}s').format(
                    seconds, max_secs), status.HTTP_400_BAD_REQUEST)

        def call():
            vm = VM.objects.get(id=body['vmid'])
            vm.sched_override_state = state
            if state == None:
                vm.sched_override_tstamp = None
            else:
                now = datetime.datetime.utcnow().replace(tzinfo=utc)
                vm.sched_override_tstamp = now.timestamp() + seconds
            vm.save()
            vm.full_clean()
        retry_in_transaction(call)

        if state is None:
            msg = 'Cleared scheduling override'
        else:
            msg = 'Override schedule, keep {} for {} seconds'.format(
                    'ON' if state else 'OFF', seconds)
        aud.info(msg, user_id=request.user.id, vm_id=vm.id)

        if request.META['SERVER_NAME'] == "testserver":
            # Don't perform other actions when running tests
            return HttpResponse()

        # the update task triggers a power on/off if needed
        vm.controller().update_status()

        return HttpResponse()
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id, vm_id=vm.id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def change_vm_schedule(request):
    """
    Change the schedule of a VM.

    JSON request body:
    {
        vmid: int,
        scheduleid: int,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    # extract the vm_id to use in logging below
    try:
        body = json.loads(request.read().decode('utf-8'))
        vm_id = body['vmid']
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def call():
        """
        Do the work, return the response and an optional callable.

        This function is safe to retry via retry_in_transaction(…).
        """
        try:
            vm = VM.objects.get(id=vm_id)
            schedule_id = body['scheduleid']
            schedule = Schedule.objects.get(id=schedule_id)
        except ObjectDoesNotExist as e:
            return get_http_json_err('{}'.format(e),
                    status.HTTP_404_NOT_FOUND), None

        if not can_do(request.user, Actions.CHANGE_VM_SCHEDULE,
                {'vm': vm, 'schedule': schedule}):
            return get_http_json_err('You may not set this VM ' +
                    'to this schedule', status.HTTP_403_FORBIDDEN), None

        vm.schedule = schedule
        vm.save()
        vm.full_clean()

        aud.info('Changed schedule to {}'.format(schedule_id),
                user_id=request.user.id, vm_id=vm_id)
        # Just in case this lambda could cause retry_in_transaction(…)
        # to re-execute this function, don't run the lambda here but return it
        # to our caller.
        return HttpResponse(), lambda: vm.controller().update_status()

    try:
        response, callback = retry_in_transaction(call)

        if request.META['SERVER_NAME'] == "testserver":
            # Don't perform other actions when running tests
            return response

        if callback:
            callback()
        return response
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id, vm_id=vm_id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def set_expiration(request):
    """
    Set the expires_at of an Expiration object.

    JSON request body:
    {
        id: int,
        timestamp: int,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        body = json.loads(request.read().decode('utf-8'))
        exp_id, tstamp = body['id'], body['timestamp']
        controller = vimma.expiry.get_controller(exp_id)
        if not controller.can_set_expiry_date(tstamp, request.user.id):
            return get_http_json_err('You may not set this Expiration ' +
                    'object to this value', status.HTTP_403_FORBIDDEN)

        naive = datetime.datetime.utcfromtimestamp(tstamp)
        aware = pytz.utc.localize(naive)
        # used for logging, if applicable
        vm_id = None

        def call():
            nonlocal vm_id
            exp = Expiration.objects.get(id=exp_id)
            exp.expires_at = aware
            if exp.type == Expiration.TYPE_VM:
                vm_id = exp.vmexpiration.vm.id
            exp.save()
        retry_in_transaction(call)

        aud.info('Changed expiration id {} to {}'.format(exp_id, aware),
                user_id=request.user.id, vm_id=vm_id)

        return HttpResponse()
    except Expiration.DoesNotExist as e:
        return get_http_json_err('{}'.format(e),
                status.HTTP_404_NOT_FOUND)
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def create_firewall_rule(request):
    """
    Create a new firewall rule.

    JSON request body:
    {
        vmid: int,
        data: provider-specific,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        body = json.loads(request.read().decode('utf-8'))
        vm_id, data = body['vmid'], body['data']
        vm = TODO_VM_CHOICE.objects.get(pk=vm_id)
        controller = vmutil.get_vm_controller(vm_id)
        if not vm.controller().can_change_firewall_rules(request.user):
            return get_http_json_err('You may not change firewall rules ' +
                    'for this VM', status.HTTP_403_FORBIDDEN)

        if request.META['SERVER_NAME'] == "testserver":
            # Don't create the firewall rule when running tests
            return HttpResponse()

        vm.controller().create_firewall_rule(data, user_id=request.user.id)
        return HttpResponse()
    except VM.DoesNotExist as e:
        return get_http_json_err('{}'.format(e),
                status.HTTP_404_NOT_FOUND)
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


@login_required_or_forbidden
def delete_firewall_rule(request):
    """
    Delete a firewall rule.

    JSON request body:
    {
        id: int,
    }
    """
    if request.method != 'POST':
        return get_http_json_err('Method “' + request.method +
            '” not allowed. Use POST instead.',
            status.HTTP_405_METHOD_NOT_ALLOWED)

    try:
        body = json.loads(request.read().decode('utf-8'))
        rule_id = body['id']
        def call():
            return FirewallRule.objects.get(id=rule_id).vm.id
        vm_id = retry_in_transaction(call)
        controller = vmutil.get_vm_controller(vm_id)
        if not controller.can_change_firewall_rules(request.user.id):
            return get_http_json_err('You may not change firewall rules ' +
                    'for this VM', status.HTTP_403_FORBIDDEN)

        if request.META['SERVER_NAME'] == "testserver":
            # Don't delete the firewall rule when running tests
            return HttpResponse()

        controller.delete_firewall_rule(rule_id, user_id=request.user.id)
        return HttpResponse()
    except FirewallRule.DoesNotExist as e:
        return get_http_json_err('{}'.format(e),
                status.HTTP_404_NOT_FOUND)
    except:
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)

