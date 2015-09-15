from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from dummy.models import (DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog,
        DummyVMExpiration, DummyFirewallRule, DummyFirewallRuleExpiration,)

from vimma.viewsets import (BaseSerializer, VMSerializer, VMExpirationSerializer, FirewallRuleSerializer, FirewallRuleExpirationSerializer,
        AuditViewSet, PowerLogViewSet, VMViewSet, VMExpirationViewSet, FirewallRuleViewSet, FirewallRuleExpirationViewSet,
        default_fields,)

class DummyProviderSerializer(BaseSerializer):
    class Meta:
        model = DummyProvider
        fields = default_fields(DummyProvider)+('config',)
        depth = 1

class DummyVMConfigSerializer(BaseSerializer):
    class Meta:
        model = DummyVMConfig

class DummyVMSerializer(VMSerializer):
    class Meta(VMSerializer.Meta):
        model = DummyVM

class DummyAuditSerializer(BaseSerializer):
    class Meta:
        model = DummyAudit

class DummyPowerLogSerializer(BaseSerializer):
    class Meta:
        model = DummyPowerLog

class DummyVMExpirationSerializer(VMExpirationSerializer):
    class Meta:
        model = DummyVMExpiration
        depth = 1

class DummyFirewallRuleSerializer(FirewallRuleSerializer):
    class Meta:
        model = DummyFirewallRule

class DummyFirewallRuleExpirationSerializer(FirewallRuleExpirationSerializer):
    class Meta:
        model = DummyFirewallRuleExpiration

# 
# 
# 

class DummyProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyProviderSerializer
    queryset = DummyProvider.objects.all()

class DummyVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyVMConfigSerializer
    queryset = DummyVMConfig.objects.all()

class DummyVMViewSet(VMViewSet):
    serializer_class = DummyVMSerializer

class DummyVMExpirationViewSet(VMExpirationViewSet):
    serializer_class = DummyVMExpirationSerializer

class DummyAuditViewSet(AuditViewSet):
    serializer_class = DummyAuditSerializer

class DummyPowerLogViewSet(PowerLogViewSet):
    serializer_class = DummyPowerLogSerializer

class DummyFirewallRuleViewSet(FirewallRuleViewSet):
    serializer_class = DummyFirewallRuleSerializer

class DummyFirewallRuleExpirationViewSet(FirewallRuleExpirationViewSet):
    serializer_class = DummyFirewallRuleExpirationSerializer
