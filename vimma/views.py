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
    Audit, PowerLog, Expiration, VMExpiration,
    FirewallRule, FirewallRuleExpiration,
)
from dummy.models import DummyProvider, DummyVMConfig, DummyVM
from aws.models import AWSProvider, AWSVMConfig, AWSVM, AWSFirewallRule

from vimma.util import (
        can_do, login_required_or_forbidden, get_http_json_err,
        retry_in_transaction,
)
from vimmasite.pagination import VimmaPagination


aud = Auditor(__name__)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'projects',)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id', 'projects',)


class TimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimeZone

class TimeZoneViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TimeZoneSerializer
    queryset = TimeZone.objects.all()
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)


class SchedulePermission(BasePermission):
    """
    Everyone can read Schedules, only users with permissions may write them.
    """
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        return can_do(request.user, Actions.WRITE_SCHEDULES)

class ScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Schedule

class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    queryset = Schedule.objects.all()
    permission_classes = (IsAuthenticated, SchedulePermission,)
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project

class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProjectSerializer
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return Project.objects.filter()
        return user.projects


class DummyProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyProvider

class DummyProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyProviderSerializer
    queryset = DummyProvider.objects.all()

class AWSProviderSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return '{} {}'.format(obj.name, obj.route_53_zone)

    class Meta:
        model = AWSProvider
        fields = ('id', 'name', 'full_name', 'route_53_zone',)

class AWSProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSProviderSerializer
    queryset = AWSProvider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

class DummyVMConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyVMConfig

class DummyVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyVMConfigSerializer
    queryset = DummyVMConfig.objects.all()

class AWSVMConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSVMConfig

class AWSVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSVMConfigSerializer
    queryset = AWSVMConfig.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)


class VMSerializer(serializers.ModelSerializer):
    class Meta:
        model = VM
        depth = 1

class VMViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VMSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('project',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return VM.objects.filter()

        # This also works, but Mihai doesn't know if it hides any traps, e.g.
        # by comparing objects instead of integers:
        #return VM.objects.filter(project__in=user.projects.filter())

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return VM.objects.filter(project__id__in=prj_ids)


class DummyVMSerializer(serializers.ModelSerializer):
    isOn = serializers.SerializerMethodField()

    def get_isOn(self, obj):
        return obj.isOn()

    class Meta:
        model = DummyVM
        depth = 1

class DummyVMViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyVMSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return DummyVM.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return DummyVM.objects.filter(vm__project__id__in=prj_ids)


class AWSVMSerializer(serializers.ModelSerializer):
    isOn = serializers.SerializerMethodField('isOn')
    class Meta:
        model = AWSVM

class AWSVMViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSVMSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('name',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return AWSVM.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return AWSVM.objects.filter(vm__project__id__in=prj_ids)


class AuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audit

class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('user',)
    ordering = ('-timestamp')

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ALL_AUDITS):
            queryset = Audit.objects.filter()
        else:
            projects = user.projects.all()
            prj_ids = [p.id for p in projects]
            queryset = Audit.objects.filter(Q(vm__project__id__in=prj_ids) |
                    Q(user__id=user.id))

        min_lvl = self.request.QUERY_PARAMS.get('min_level', None)
        if min_lvl is not None:
            queryset = queryset.filter(level__gte=min_lvl)
        return queryset


audit_levels_json = json.dumps([{'id': c[0], 'name': c[1]}
    for c in Audit.LEVEL_CHOICES])


class PowerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PowerLog

class PowerLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PowerLogSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('id',)
    ordering = ('-timestamp',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ALL_POWER_LOGS):
            return PowerLog.objects.filter()
        else:
            projects = user.projects.all()
            prj_ids = [p.id for p in projects]
            return PowerLog.objects.filter(vm__project__id__in=prj_ids)


class VMExpirationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VMExpiration

class VMExpirationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = VMExpirationSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

    def get_queryset(self):
        user = self.request.user

        if can_do(user, Actions.READ_ANY_PROJECT):
            return VMExpiration.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return VMExpiration.objects.filter(vm__project__id__in=prj_ids)


class FirewallRuleExpirationSerializer(serializers.ModelSerializer):
    class Meta:
        model = FirewallRuleExpiration
        depth = 2

class FirewallRuleExpirationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FirewallRuleExpirationSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('firewallrule',)

    def get_queryset(self):
        user = self.request.user

        if can_do(user, Actions.READ_ANY_PROJECT):
            return FirewallRuleExpiration.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return FirewallRuleExpiration.objects.filter(
                firewallrule__vm__project__id__in=prj_ids)


class FirewallRuleSerializer(serializers.ModelSerializer):
    expiration = FirewallRuleExpirationSerializer()

    class Meta:
        model = FirewallRule
        fields = ('id','expiration',)
        depth = 1

class FirewallRuleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = FirewallRuleSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return FirewallRule.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return FirewallRule.objects.filter(vm__project__id__in=prj_ids)


class AWSFirewallRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSFirewallRule
        depth = 2

class AWSFirewallRuleViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSFirewallRuleSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('firewallrule',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return AWSFirewallRule.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return AWSFirewallRule.objects.filter(
                firewallrule__vm__project__id__in=prj_ids)

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

    # TODO: type inormation provided by client for AWS/Dummy/..
    config_type = DummyConfig

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

    try:
        vmutil.create_vm(vmconf, prj, schedule, body['comment'], body['data'],
                request.user.id)
        return HttpResponse()
    except Exception as e:
        print(e)
        lines = traceback.format_exception_only(*sys.exc_info()[:2])
        msg = ''.join(lines)
        aud.error(msg, user_id=request.user.id)
        return get_http_json_err(msg, status.HTTP_500_INTERNAL_SERVER_ERROR)


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
        controller = vmutil.get_vm_controller(vm_id)
        if not controller.can_change_firewall_rules(request.user.id):
            return get_http_json_err('You may not change firewall rules ' +
                    'for this VM', status.HTTP_403_FORBIDDEN)

        if request.META['SERVER_NAME'] == "testserver":
            # Don't create the firewall rule when running tests
            return HttpResponse()

        controller.create_firewall_rule(data, user_id=request.user.id)
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

