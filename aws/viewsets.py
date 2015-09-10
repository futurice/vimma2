from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from aws.models import AWSProvider, AWSVMConfig, AWSVM, AWSFirewallRule, AWSAudit, AWSPowerLog, AWSVMExpiration
from vimma.viewsets import BaseSerializer, VMSerializer, AuditViewSet, PowerLogViewSet, VMViewSet, FirewallRuleViewSet, default_fields

class AWSVMExpirationSerializer(BaseSerializer):
    class Meta:
        model = AWSVMExpiration

class AWSProviderSerializer(BaseSerializer):
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return '{} {}'.format(obj.name, obj.route_53_zone)

    class Meta:
        model = AWSProvider
        fields = default_fields(AWSProvider,
                    exclude=['ssh_key_name','access_key_id','access_key_secret'])\
                    +('full_name','config','content_type',)
        depth = 1
class AWSVMConfigSerializer(BaseSerializer):
    class Meta:
        model = AWSVMConfig
        depth = 1

class AWSVMSerializer(VMSerializer):
    class Meta:
        model = AWSVM
        depth = 1

class AWSAuditSerializer(BaseSerializer):
    class Meta:
        model = AWSAudit

class AWSAuditViewSet(AuditViewSet):
    serializer_class = AWSAuditSerializer

class AWSPowerLogSerializer(BaseSerializer):
    class Meta:
        model = AWSPowerLog

class AWSPowerLogViewSet(PowerLogViewSet):
    serializer_class = AWSPowerLogSerializer

class AWSFirewallRuleSerializer(BaseSerializer):
    class Meta:
        model = AWSFirewallRule
        depth = 2


# viewsets

class AWSProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSProviderSerializer
    queryset = AWSProvider.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)


class AWSVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AWSVMConfigSerializer
    queryset = AWSVMConfig.objects.all()
    filter_backends = (filters.DjangoFilterBackend,)
    filter_fields = ('id',)


class AWSVMViewSet(VMViewSet):
    serializer_class = AWSVMSerializer

class AWSFirewallRuleViewSet(FirewallRuleViewSet):
    serializer_class = AWSFirewallRuleSerializer
