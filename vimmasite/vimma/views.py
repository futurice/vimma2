from django.contrib.auth.models import User
from django.shortcuts import render
from rest_framework import viewsets, routers, filters, serializers
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

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
    filter_fields = ('projects',)

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
        fields = ('id', 'visible_field',)

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

    def get_queryset(self):
        user = self.request.user
        if can_do(user, Actions.READ_ANY_PROJECT):
            return DummyVM.objects.filter()

        projects = user.profile.projects.all()
        prj_ids = [p.id for p in projects]
        return DummyVM.objects.filter(vm__project__id__in=prj_ids)


class AWSVMViewSet(viewsets.ReadOnlyModelViewSet):
    model = AWSVM

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
