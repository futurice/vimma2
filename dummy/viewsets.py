from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from dummy.models import (Provider, Config, VM, Audit, PowerLog,
        Expiration, FirewallRule, FirewallRuleExpiration,)

from vimma.viewsets import (BaseSerializer, VMSerializer, ExpirationSerializer, FirewallRuleSerializer, FirewallRuleExpirationSerializer,
        AuditViewSet, PowerLogViewSet, VMViewSet, ExpirationViewSet, FirewallRuleViewSet, FirewallRuleExpirationViewSet,
        default_fields,)

class ProviderSerializer(BaseSerializer):
    class Meta:
        model = Provider
        fields = default_fields(Provider)+('config',)
        depth = 1

class ConfigSerializer(BaseSerializer):
    class Meta:
        model = Config

class VMSerializer(VMSerializer):
    class Meta(VMSerializer.Meta):
        model = VM

class AuditSerializer(BaseSerializer):
    class Meta:
        model = Audit

class PowerLogSerializer(BaseSerializer):
    class Meta:
        model = PowerLog

class ExpirationSerializer(ExpirationSerializer):
    class Meta:
        model = Expiration
        depth = 1

class FirewallRuleSerializer(FirewallRuleSerializer):
    class Meta:
        model = FirewallRule

class FirewallRuleExpirationSerializer(FirewallRuleExpirationSerializer):
    class Meta:
        model = FirewallRuleExpiration

# 
# 
# 

class ProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProviderSerializer
    queryset = Provider.objects.all()

class ConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ConfigSerializer
    queryset = Config.objects.all()

class VMViewSet(VMViewSet):
    serializer_class = VMSerializer

class ExpirationViewSet(ExpirationViewSet):
    serializer_class = ExpirationSerializer

class AuditViewSet(AuditViewSet):
    serializer_class = AuditSerializer

class PowerLogViewSet(PowerLogViewSet):
    serializer_class = PowerLogSerializer

class FirewallRuleViewSet(FirewallRuleViewSet):
    serializer_class = FirewallRuleSerializer

class FirewallRuleExpirationViewSet(FirewallRuleExpirationViewSet):
    serializer_class = FirewallRuleExpirationSerializer
