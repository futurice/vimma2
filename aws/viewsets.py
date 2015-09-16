from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from aws.models import Provider, Config, VM, FirewallRule, PowerLog, Expiration, FirewallRuleExpiration
from vimma.viewsets import (BaseSerializer, VMSerializer, ExpirationSerializer, FirewallRuleSerializer, FirewallRuleExpirationSerializer,
        PowerLogViewSet, VMViewSet, FirewallRuleViewSet, ExpirationViewSet, FirewallRuleExpirationViewSet,
        default_fields)

class ProviderSerializer(BaseSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return '{} {}'.format(obj.name, obj.route_53_zone)

    class Meta:
        model = Provider
        fields = default_fields(Provider,
                    exclude=['ssh_key_name','access_key_id','access_key_secret'])\
                    +('full_name','config','content_type',)
        depth = 1

class ConfigSerializer(BaseSerializer):
    class Meta:
        model = Config
        depth = 1

class VMSerializer(VMSerializer):
    class Meta(VMSerializer.Meta):
        model = VM

class PowerLogSerializer(BaseSerializer):
    class Meta:
        model = PowerLog

class ExpirationSerializer(BaseSerializer):
    class Meta:
        model = Expiration

class FirewallRuleSerializer(FirewallRuleSerializer):
    class Meta:
        model = FirewallRule
        depth = 2

class FirewallRuleExpirationSerializer(FirewallRuleExpirationSerializer):
    class Meta:
        model = FirewallRuleExpiration
        depth = 1


# 
#
# 

class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

class ConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConfigSerializer
    queryset = Config.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

class VMViewSet(VMViewSet):
    serializer_class = VMSerializer

class ExpirationViewSet(ExpirationViewSet):
    serializer_class = ExpirationSerializer

class PowerLogViewSet(PowerLogViewSet):
    serializer_class = PowerLogSerializer

class FirewallRuleViewSet(FirewallRuleViewSet):
    serializer_class = FirewallRuleSerializer

class FirewallRuleExpirationViewSet(FirewallRuleExpirationViewSet):
    serializer_class = FirewallRuleExpirationSerializer
