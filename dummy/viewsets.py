from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from dummy.models import DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog

from vimma.viewsets import VMSerializer, AuditViewSet, PowerLogViewSet, VMViewSet

def default_fields(model):
    return tuple([k.name for k in DummyProvider._meta.fields])

class DummyProviderSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyProvider
        fields = default_fields(DummyProvider)+('config',)
        depth = 1

class DummyProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyProviderSerializer
    queryset = DummyProvider.objects.all()

class DummyVMConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyVMConfig

class DummyVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyVMConfigSerializer
    queryset = DummyVMConfig.objects.all()

class DummyVMSerializer(VMSerializer):
    class Meta:
        model = DummyVM
        depth = 1

class DummyVMViewSet(VMViewSet):
    serializer_class = DummyVMSerializer

class DummyAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyAudit

class DummyAuditViewSet(AuditViewSet):
    serializer_class = DummyAuditSerializer

class DummyPowerLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = DummyPowerLog

class DummyPowerLogViewSet(PowerLogViewSet):
    serializer_class = DummyPowerLogSerializer
