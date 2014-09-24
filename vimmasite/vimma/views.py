from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import render
import json
from rest_framework import viewsets, routers, filters, serializers
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)
import sys
import traceback

from vimma import vmutil
from vimma.models import (
    Profile, Schedule, TimeZone, Project, Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
    VM, DummyVM, AWSVM,
)
from vimma.actions import Actions
from vimma.util import can_do, login_required_or_forbidden


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('id', 'user', 'projects')

class ProfileViewSet(viewsets.ReadOnlyModelViewSet):
    model = Profile
    serializer_class = ProfileSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('projects', 'user')

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    model = User
    serializer_class = UserSerializer


class TimeZoneViewSet(viewsets.ReadOnlyModelViewSet):
    model = TimeZone
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

class ScheduleViewSet(viewsets.ModelViewSet):
    model = Schedule
    permission_classes = (IsAuthenticated, SchedulePermission,)
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)


class ProjectViewSet(viewsets.ReadOnlyModelViewSet):
    model = Project
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return Project.objects.filter()
        return user.profile.projects


class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    model = Provider
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)

class DummyProviderViewSet(viewsets.ReadOnlyModelViewSet):
    model = DummyProvider

class AWSProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSProvider
        fields = ('id',)

class AWSProviderViewSet(viewsets.ReadOnlyModelViewSet):
    model = AWSProvider
    serializer_class = AWSProviderSerializer


class VMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    model = VMConfig
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)

class DummyVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    model = DummyVMConfig

class AWSVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    model = AWSVMConfig


class VMViewSet(viewsets.ReadOnlyModelViewSet):
    model = VM
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('project',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return VM.objects.filter()

        # This also works, but Mihai doesn't know if it hides any traps, e.g.
        # by comparing objects instead of integers:
        #return VM.objects.filter(project__in=user.profile.projects.filter())

        projects = user.profile.projects.all()
        prj_ids = [p.id for p in projects]
        return VM.objects.filter(project__id__in=prj_ids)


class DummyVMViewSet(viewsets.ReadOnlyModelViewSet):
    model = DummyVM
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('vm',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return DummyVM.objects.filter()

        projects = user.profile.projects.all()
        prj_ids = [p.id for p in projects]
        return DummyVM.objects.filter(vm__project__id__in=prj_ids)


class AWSVMViewSet(viewsets.ReadOnlyModelViewSet):
    model = AWSVM
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('vm',)

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return AWSVM.objects.filter()

        projects = user.profile.projects.all()
        prj_ids = [p.id for p in projects]
        return AWSVM.objects.filter(vm__project__id__in=prj_ids)


@login_required_or_forbidden
def index(request):
    """
    Homepage.
    """
    return render(request, 'vimma/index.html')


@login_required_or_forbidden
def test(request):
    """
    JavaScript Unit Tests.
    """
    return render(request, 'vimma/test.html')


@login_required_or_forbidden
def createVM(request):
    """
    Create a new VM.

    JSON request body:
    {
        project: int,
        vmconfig: int,
        schedule: int,
        data: «provider-specific data»,
    }
    """
    def getHttpErr(errText, code):
        return HttpResponse(json.dumps({'error': errText}),
            content_type="application/json", status=code)

    if request.method != 'POST':
        return getHttpErr('Method “' + request.method +
            '” not allowed. Use POST instead.', 405)

    body = json.loads(request.read().decode('utf-8'))

    try:
        prj = Project.objects.get(id=body['project'])
        vmconf = VMConfig.objects.get(id=body['vmconfig'])
        schedule = Schedule.objects.get(id=body['schedule'])
    except ObjectDoesNotExist as e:
        return getHttpErr('{}'.format(e), 404)

    if not can_do(request.user, Actions.CREATE_VM_IN_PROJECT, prj):
        return getHttpErr('You may not create VMs in this project', 403)

    if vmconf.default_schedule.id != schedule.id:
        if not can_do(request.user, Actions.USE_SCHEDULE, schedule):
            return getHttpErr('You may not use this schedule', 403)

    if request.META['SERVER_NAME'] == "testserver":
        # Don't create the VMs when running tests
        return HttpResponse()

    try:
        vmutil.createVM(vmconf, prj, schedule, body['data'])
        return HttpResponse()
    except:
        msg = traceback.format_exception_only(*sys.exc_info()[:2])
        return getHttpErr(msg, 500)
