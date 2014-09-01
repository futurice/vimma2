from django.conf.urls import patterns, url, include
from rest_framework import routers

from vimma.views import (
    TimeZoneViewSet, ScheduleViewSet, ProjectViewSet,
    ProviderViewSet, DummyProviderViewSet, AWSProviderViewSet,
    VMConfigViewSet, DummyVMConfigViewSet, AWSVMConfigViewSet,
    index, test,
)


router = routers.DefaultRouter()
router.register(r'timezones', TimeZoneViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'providers', ProviderViewSet)
router.register(r'dummyproviders', DummyProviderViewSet)
router.register(r'awsproviders', AWSProviderViewSet)
router.register(r'vmconfigs', VMConfigViewSet)
router.register(r'dummyvmconfigs', DummyVMConfigViewSet)
router.register(r'awsvmconfigs', AWSVMConfigViewSet)

urlpatterns = patterns('',
    url(r'^api/', include(router.urls)),
    url(r'^$', index, name='index'),
    url(r'^test$', test, name='test'),
)
