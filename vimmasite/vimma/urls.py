from django.conf.urls import patterns, url, include
from rest_framework import routers

from vimma.views import (
    ProfileViewSet, UserViewSet,
    TimeZoneViewSet, ScheduleViewSet, ProjectViewSet,
    ProviderViewSet, DummyProviderViewSet, AWSProviderViewSet,
    VMConfigViewSet, DummyVMConfigViewSet, AWSVMConfigViewSet,
    VMViewSet, DummyVMViewSet, AWSVMViewSet,
    AuditViewSet,
    index, base_js, test,
    create_vm, power_on_vm, power_off_vm, reboot_vm, destroy_vm,
    override_schedule, change_vm_schedule,
)


router = routers.DefaultRouter()
router.register(r'profiles', ProfileViewSet)
router.register(r'users', UserViewSet)
router.register(r'timezones', TimeZoneViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'projects', ProjectViewSet)
router.register(r'providers', ProviderViewSet)
router.register(r'dummyproviders', DummyProviderViewSet)
router.register(r'awsproviders', AWSProviderViewSet)
router.register(r'vmconfigs', VMConfigViewSet)
router.register(r'dummyvmconfigs', DummyVMConfigViewSet)
router.register(r'awsvmconfigs', AWSVMConfigViewSet)
router.register(r'vms', VMViewSet)
router.register(r'dummyvms', DummyVMViewSet)
router.register(r'awsvm', AWSVMViewSet)
router.register(r'audit', AuditViewSet)

urlpatterns = patterns('',
    url(r'^api/', include(router.urls)),

    url(r'^$', index, name='index'),
    url(r'^base.js$', base_js, name='base_js'),
    url(r'^test$', test, name='test'),

    url(r'^createvm$', create_vm, name='createVM'),
    url(r'^poweronvm$', power_on_vm, name='powerOnVM'),
    url(r'^poweroffvm$', power_off_vm, name='powerOffVM'),
    url(r'^rebootvm$', reboot_vm, name='rebootVM'),
    url(r'^destroyvm$', destroy_vm, name='destroyVM'),

    url(r'^override-schedule$', override_schedule, name='overrideSchedule'),
    url(r'^change-vm-schedule$', change_vm_schedule, name='changeVMSchedule'),
)
