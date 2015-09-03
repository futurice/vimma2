import json

from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)
from vimma.models import (
    Schedule, TimeZone, Project,
    User, VM,
    Audit, Expiration, VMExpiration,
    FirewallRule, FirewallRuleExpiration,
)
from vimma.actions import Actions
from vimma.util import (
        can_do, login_required_or_forbidden, get_http_json_err,
        retry_in_transaction,
)


def default_fields(model):
    return tuple([k.name for k in model._meta.fields])

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

class VMSerializer(serializers.ModelSerializer):
    isOn = serializers.SerializerMethodField()

    def get_isOn(self, obj):
        return obj.isOn()

class VMViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('project','name',)

    def get_queryset(self):
        user = self.request.user
        model = self.serializer_class.Meta.model
        if can_do(user, Actions.READ_ANY_PROJECT):
            return model.objects.filter()

        prj_ids = [p.id for p in user.projects.all()]
        return model.objects.filter(project__id__in=prj_ids)

class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('user','vm',)
    ordering = ('-timestamp')

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        user = self.request.user
        if can_do(user, Actions.READ_ALL_AUDITS):
            queryset = model.objects.filter()
        else:
            projects = user.projects.all()
            prj_ids = [p.id for p in projects]
            queryset = model.objects.filter(Q(vm__project__id__in=prj_ids) |
                    Q(user__id=user.id))

        min_lvl = self.request.query_params.get('min_level', None)
        if min_lvl is not None:
            queryset = queryset.filter(level__gte=min_lvl)
        return queryset

class PowerLogViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('vm',)
    ordering = ('-timestamp',)

    def get_queryset(self):
        user = self.request.user
        model = self.serializer_class.Meta.model
        if can_do(user, Actions.READ_ALL_POWER_LOGS):
            return model.objects.filter()
        else:
            projects = user.projects.all()
            prj_ids = [p.id for p in projects]
            return model.objects.filter(vm__project__id__in=prj_ids)

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
        model = self.serializer_class.Meta.model

        if can_do(user, Actions.READ_ANY_PROJECT):
            return model.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return model.objects.filter(
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
        model = self.serializer_class.Meta.model
        if can_do(user, Actions.READ_ANY_PROJECT):
            return model.objects.filter()

        projects = user.projects.all()
        prj_ids = [p.id for p in projects]
        return model.objects.filter(vm__project__id__in=prj_ids)

