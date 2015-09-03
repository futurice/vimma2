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
from dummy.models import DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog
from aws.models import AWSProvider, AWSVMConfig, AWSVM, AWSFirewallRule, AWSAudit, AWSPowerLog

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


class DummyAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyAudit

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

class DummyAuditViewSet(AuditViewSet):
    serializer_class = DummyAuditSerializer

class AWSAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSAudit

class AWSAuditViewSet(AuditViewSet):
    serializer_class = AWSAuditSerializer

audit_levels_json = json.dumps([{'id': c[0], 'name': c[1]}
    for c in Audit.LEVEL_CHOICES])


class DummyPowerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyPowerLog

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

class DummyPowerLogViewSet(PowerLogViewSet):
    serializer_class = DummyPowerLogSerializer

class AWSPowerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSPowerLog

class AWSPowerLogViewSet(PowerLogViewSet):
    serializer_class = AWSPowerLogSerializer


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
