import json, copy

from django.contrib.contenttypes.models import ContentType

from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)
from rest_framework.reverse import reverse

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

from rest_framework.utils.field_mapping import (get_nested_relation_kwargs,)

def info():
    # map models to viewsets
    from vimma.urls import router
    return {k[1].serializer_class.Meta.model:k[1] for k in router.registry}

def default_fields(model, serializer=None, exclude=[]):
    # TODO: add content_type, if found in serializer's fields
    fields = [k.name for k in model._meta.fields]
    return tuple(filter(lambda x: None if x in exclude else x, fields))

class BaseSerializer(serializers.ModelSerializer):
    content_type = serializers.SerializerMethodField()

    def get_content_type(self, obj):
        value = ContentType.objects.get_for_model(obj)
        return {'id': value.id, 'name': value.model, 'url': reverse('{}-list'.format(value.model)),}

    def build_nested_field(self, field_name, relation_info, nested_depth):
        # By default only Model information is kept; re-use our own Serializers
        # TODO: metaprogramming to set depth, to keep serializer Meta intact
        try:
            base_cls = info()[relation_info.related_model].serializer_class
        except Exception as e:
            print("Missing ViewSet for {}: {}".format(relation_info.related_model, e))
            base_cls = serializers.ModelSerializer

        class NestedSerializer(base_cls):
            class Meta:
                model = relation_info.related_model
                depth = nested_depth - 1
        field_class = NestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)
        return field_class, field_kwargs

class UserSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'projects',) + ('content_type',)

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id', 'projects',)

class TimeZoneSerializer(BaseSerializer):
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

class ScheduleSerializer(BaseSerializer):
    class Meta:
        model = Schedule

class ScheduleViewSet(viewsets.ModelViewSet):
    serializer_class = ScheduleSerializer
    queryset = Schedule.objects.all()
    permission_classes = (IsAuthenticated, SchedulePermission,)
    filter_backends = (filters.OrderingFilter,)
    ordering = ('name',)

class ProjectSerializer(BaseSerializer):
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

class VMSerializer(BaseSerializer):
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

class VMExpirationSerializer(BaseSerializer):
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

class FirewallRuleExpirationSerializer(BaseSerializer):
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

class FirewallRuleSerializer(BaseSerializer):
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

