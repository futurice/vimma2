import json, copy

from django.contrib.contenttypes.models import ContentType
from django.utils.timezone import utc
from django.db.models import Q

from rest_framework.response import Response
from rest_framework.decorators import detail_route, list_route

from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)
from rest_framework.reverse import reverse

from vimma.models import (
    Schedule, TimeZone, Project,
    User, VM, Audit,
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

    def __init__(self, *args, **kwargs):
        if self.get_meta_fields():
            self.Meta.fields = self.get_meta_fields()
        super().__init__(*args, **kwargs)

    def get_meta_fields(self):
        return None

    def get_content_type(self, obj):
        value = ContentType.objects.get_for_model(obj)
        module_name = value.model_class().__module__.split('.')[0]
        module_name = module_name.replace('vimma', '')
        return {'id': value.id, 'app_label': value.app_label, 'model': value.model, 'url': reverse('{}{}-list'.format(module_name, value.model)),}

    def build_nested_field(self, field_name, relation_info, nested_depth):
        # By default only Model information is kept; re-use our own Serializers
        # TODO: metaprogramming to set depth, to keep serializer Meta intact
        try:
            base_cls = info()[relation_info.related_model].serializer_class
        except Exception as e:
            print("Missing ViewSet for {}: {}".format(relation_info.related_model, e))
            base_cls = serializers.ModelSerializer
            base_cls.Meta = object

        # TODO: configurable nested depths
        if relation_info.related_model == User:
            nested_depth = min(nested_depth, 1)

        class NestedSerializer(base_cls):
            class Meta(base_cls.Meta):
                model = relation_info.related_model
                depth = nested_depth - 1

        field_class = NestedSerializer
        field_kwargs = get_nested_relation_kwargs(relation_info)
        return field_class, field_kwargs

class UserSerializer(BaseSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email', 'projects', 'roles',) + ('content_type',)
        depth = 2

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

    def get_meta_fields(self):
        return default_fields(self.Meta.model)+('expiration','firewallrule',) + ('content_type',)

    class Meta:
        model = VM
        depth = 2

class VMViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('project','name','id',)

    def get_queryset(self):
        user = self.request.user
        model = self.serializer_class.Meta.model
        if can_do(user, Actions.READ_ANY_PROJECT):
            return model.objects.filter()

        return model.objects.filter(project__id__in=user.projects.all().values_list('id'))

    @list_route(methods=['post'])
    def create(self, request):
        body = json.loads(request.read().decode('utf-8'))
        model = self.serializer_class.Meta.model
        config_model = model._meta.get_field('config').related_model
        try:
            project = Project.objects.get(id=body['project'])
            vmconf = config_model.objects.get(id=body['config'])
            schedule = Schedule.objects.get(id=body['schedule'])
        except ObjectDoesNotExist as e:
            return Response('{}'.format(e), status=status.HTTP_404_NOT_FOUND)

        if not can_do(request.user, Actions.CREATE_VM_IN_PROJECT, project):
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

        request.user.auditor.debug('Request to create VM')

        model().controller().create_vm(
                project=project,
                schedule=schedule,
                config=vmconf,
                user=request.user,

                name=body.get('name'),
                comment=body.get('comment'),)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def power_on(self, request, pk=None):
        obj = self.get_object()
        if not can_do(request.user,
                Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT, obj.project):
            return Response('You may not power on VMs in this project',
                    status=status.HTTP_403_FORBIDDEN)
        obj.auditor.debug('Request to Power ON', user_id=request.user.id)
        obj.controller().power_on(user_id=self.request.user)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def power_off(self, request, pk=None):
        obj = self.get_object()
        if not can_do(request.user,
                Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT, obj.project):
            return Response('You may not power off VMs in this project',
                    status=status.HTTP_403_FORBIDDEN)
        obj.auditor.debug('Request to Power OFF', user_id=request.user.id)
        obj.controller().power_off(user_id=self.request.user)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def reboot(self, request, pk=None):
        obj = self.get_object()
        if not can_do(request.user,
                Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT, obj.project):
            return Response('You may not reboot VMs in this project',
                    status=status.HTTP_403_FORBIDDEN)
        obj.auditor.debug('Request to Reboot', user_id=request.user.id)
        obj.controller().reboot(user_id=self.request.user)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def destroy(self, request, pk=None):
        obj = self.get_object()
        if not can_do(request.user,
                Actions.POWER_ONOFF_REBOOT_DESTROY_VM_IN_PROJECT, obj.project):
            return Response('You may not destroy VMs in this project',
                    status=status.HTTP_403_FORBIDDEN)

        obj.destroy_request_at = datetime.datetime.utcnow().replace(tzinfo=utc)
        obj.destroy_request_by = request.user
        obj.save()

        obj.auditor.debug('Request to Destroy', user_id=request.user.id)
        obj.controller().destroy(user_id=self.request.user)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def override_schedule(self, request, pk=None):
        body = json.loads(request.read().decode('utf-8'))
        state = body['state'] # true,false,null

        schedule_id = body['scheduleid']
        obj = self.get_object()
        schedule = Schedule.objects.get(id=schedule_id)

        if not can_do(request.user, Actions.OVERRIDE_VM_SCHEDULE, vm):
            return Response('You may not override this VM schedule',
                    status=status.HTTP_403_FORBIDDEN)

        if state is not None:
            seconds = body['seconds']
            max_secs = obj.config.provider.max_override_seconds
            if seconds > max_secs:
                return Response(('{}s is too long, must be ≤ {}s').format(
                    seconds, max_secs), status=status.HTTP_400_BAD_REQUEST)

        obj.sched_override_state = state
        if state == None:
            obj.sched_override_tstamp = None
        else:
            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            obj.sched_override_tstamp = now.timestamp() + seconds
        obj.save()

        if state is None:
            msg = 'Cleared scheduling override'
        else:
            msg = 'Override schedule, keep {} for {} seconds'.format(
                    'ON' if state else 'OFF', seconds)
        obj.auditor.info(msg, user_id=request.user.id)
        obj.controller().update_status(user_id=self.request.user)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def change_schedule(self, request, pk=None):
        body = json.loads(request.read().decode('utf-8'))
        schedule_id = body['scheduleid']
        obj = self.get_object()
        schedule = Schedule.objects.get(id=schedule_id)

        if not can_do(request.user, Actions.CHANGE_VM_SCHEDULE,
                {'vm': vm, 'schedule': schedule}):
            return Response('You may not set this VM to this schedule',
                    status=status.HTTP_403_FORBIDDEN)

        obj.schedule = schedule
        obj.save()
        obj.auditor.info('Changed schedule to {}'.format(schedule_id), user_id=request.user.id)
        obj.controller().update_status(user_id=self.request.user)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def set_expiration(self, request, pk=None):
        # TODO: move to vmexpiration viewset, or add controller() signature
        model = self.serializer_class.Meta.model
        body = json.loads(request.read().decode('utf-8'))
        exp_id = body['expid']
        tstamp = body['timestamp']
        obj = self.get_object()
        if not obj.controller().can_set_expiry_date(tstamp, request.user.id):
            return Response('You may not set this Expiration ' +
                    'object to this value', status=status.HTTP_403_FORBIDDEN)

        naive = datetime.datetime.utcfromtimestamp(tstamp)
        aware = pytz.utc.localize(naive)

        exp_model = obj._meta.get_field('expiration').related_model
        exp = exp_model.objects.get(id=exp_id)
        exp.expires_at = aware
        exp.save()

        obj.auditor.info('Changed expiration id {} to {}'.format(exp_id, aware), user_id=request.user.id)

        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def create_firewall_rule(self, request, pk=None):
        body = json.loads(request.read().decode('utf-8'))
        obj = self.get_object()
        if not obj.controller().can_change_firewall_rules(request.user.id):
            return Response('You may not change firewall rules ' +
                    'for this VM', status=status.HTTP_403_FORBIDDEN)
        obj.controller().create_firewall_rule(body['data'], user_id=request.user.id)
        return Response({}, status=status.HTTP_200_OK)

    @detail_route(methods=['post'])
    def delete_firewall_rule(self, request, pk=None):
        obj = self.get_object()
        if not obj.controller().can_change_firewall_rules(request.user.id):
            return Response('You may not change firewall rules ' +
                    'for this VM', status=status.HTTP_403_FORBIDDEN)
        obj.controller().delete_firewall_rule(rule_id, user_id=request.user.id)
        return Response({}, status=status.HTTP_200_OK)
    

class AuditSerializer(BaseSerializer):
    class Meta:
        model = Audit

class AuditViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AuditSerializer
    filter_backends = (filters.DjangoFilterBackend, filters.OrderingFilter)
    filter_fields = ('user','object_content_type','object_id','project',)
    ordering = ('-timestamp')

    def get_queryset(self):
        model = self.serializer_class.Meta.model
        user = self.request.user
        if can_do(user, Actions.READ_ALL_AUDITS):
            queryset = model.objects.filter()
        else:
            queryset = model.objects.filter(
                    Q(project_id__in=list(user.projects.all().values_list('id'))) |
                    Q(user_id=user.id))
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
            return model.objects.filter(vm__project__id__in=user.projects.all().values_list('id'))

class ExpirationSerializer(BaseSerializer):
    pass

class ExpirationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExpirationSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

    def get_queryset(self):
        user = self.request.user
        model = self.serializer_class.Meta.model

        if can_do(user, Actions.READ_ANY_PROJECT):
            return model.objects.filter()

        return model.objects.filter(vm__project__id__in=user.projects.all().values_list('id'))

class FirewallRuleSerializer(BaseSerializer):

    def get_meta_fields(self):
        return default_fields(self.Meta.model)+('expiration',)

    class Meta:
        depth = 1

class FirewallRuleViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

    def get_queryset(self):
        user = self.request.user
        model = self.serializer_class.Meta.model
        if can_do(user, Actions.READ_ANY_PROJECT):
            return model.objects.filter()

        return model.objects.filter(vm__project__id__in=user.projects.all().values_list('id'))


class FirewallRuleExpirationSerializer(BaseSerializer):

    class Meta:
        depth = 1

class FirewallRuleExpirationViewSet(viewsets.ReadOnlyModelViewSet):
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('firewallrule',)

    def get_queryset(self):
        user = self.request.user
        model = self.serializer_class.Meta.model

        if can_do(user, Actions.READ_ANY_PROJECT):
            return model.objects.filter()

        return model.objects.filter(
                firewallrule__vm__project__id__in=user.projects.all().values_list('id'))
