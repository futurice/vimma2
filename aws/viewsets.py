from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from aws.models import AWSProvider, AWSVMConfig, AWSVM, AWSFirewallRule, AWSAudit, AWSPowerLog
from vimma.viewsets import VMSerializer, AuditViewSet, PowerLogViewSet, VMViewSet, FirewallRuleViewSet, default_fields

class AWSProviderSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return '{} {}'.format(obj.name, obj.route_53_zone)

    class Meta:
        model = AWSProvider
        fields = default_fields(AWSProvider)+('full_name','config',)
        depth = 1

class AWSProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSProviderSerializer
    queryset = AWSProvider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

class AWSVMConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSVMConfig

class AWSVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSVMConfigSerializer
    queryset = AWSVMConfig.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)

class AWSVMSerializer(VMSerializer):
    class Meta:
        model = AWSVM
        depth = 1

class AWSVMViewSet(VMViewSet):
    serializer_class = AWSVMSerializer

class AWSAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSAudit

class AWSAuditViewSet(AuditViewSet):
    serializer_class = AWSAuditSerializer

class AWSPowerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSPowerLog

class AWSPowerLogViewSet(PowerLogViewSet):
    serializer_class = AWSPowerLogSerializer

class AWSFirewallRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AWSFirewallRule
        depth = 2

class AWSFirewallRuleViewSet(FirewallRuleViewSet):
    serializer_class = AWSFirewallRuleSerializer
