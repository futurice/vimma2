from rest_framework import viewsets, routers, filters, serializers, status
from rest_framework.permissions import (
    SAFE_METHODS, BasePermission, IsAuthenticated
)

from dummy.models import DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog, DummyVMExpiration

from vimma.viewsets import BaseSerializer, VMSerializer, AuditViewSet, PowerLogViewSet, VMViewSet, default_fields

class DummyProviderSerializer(BaseSerializer):
    class Meta:
        model = DummyProvider
        fields = default_fields(DummyProvider)+('config',)
        depth = 1

class DummyVMConfigSerializer(BaseSerializer):
    class Meta:
        model = DummyVMConfig

class DummyVMSerializer(VMSerializer):
    class Meta:
        model = DummyVM
        depth = 1

class DummyAuditSerializer(BaseSerializer):
    class Meta:
        model = DummyAudit

class DummyPowerLogSerializer(BaseSerializer):
    class Meta:
        model = DummyPowerLog

class DummyVMExpiration(BaseSerializer):
    class Meta:
        model = DummyVMExpiration

class DummyProviderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyProviderSerializer
    queryset = DummyProvider.objects.all()

class DummyVMConfigViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DummyVMConfigSerializer
    queryset = DummyVMConfig.objects.all()

class DummyVMViewSet(VMViewSet):
    serializer_class = DummyVMSerializer

class DummyAuditViewSet(AuditViewSet):
    serializer_class = DummyAuditSerializer

class DummyPowerLogViewSet(PowerLogViewSet):
    serializer_class = DummyPowerLogSerializer
