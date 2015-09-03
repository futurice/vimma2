from django.conf import settings
from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rest_framework import routers

from vimma.viewsets import (
    UserViewSet,
    TimeZoneViewSet,
    ScheduleViewSet,
    ProjectViewSet,
    FirewallRuleViewSet,
    VMExpirationViewSet,
    FirewallRuleExpirationViewSet,
)

from dummy.viewsets import (
    DummyProviderViewSet,
    DummyVMConfigViewSet,
    DummyVMViewSet,
    DummyAuditViewSet,
    DummyPowerLogViewSet,
)

from aws.viewsets import (
    AWSProviderViewSet,
    AWSVMConfigViewSet,
    AWSVMViewSet,
    AWSAuditViewSet,
    AWSPowerLogViewSet,
    AWSFirewallRuleViewSet,
)

from vimma.views import (
    index, base_js, test,
    create_vm, power_on_vm, power_off_vm, reboot_vm, destroy_vm,
    override_schedule, change_vm_schedule, set_expiration,
    create_firewall_rule, delete_firewall_rule,
)


router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'timezones', TimeZoneViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'projects', ProjectViewSet, 'project')

router.register(r'dummyvms', DummyVMViewSet, 'dummyvm')
router.register(r'dummyproviders', DummyProviderViewSet)
router.register(r'dummyvmconfigs', DummyVMConfigViewSet)
router.register(r'dummyaudit', DummyAuditViewSet, 'dummyaudit')
router.register(r'dummypowerlog', DummyPowerLogViewSet, 'dummypowerlog')

router.register(r'awsvm', AWSVMViewSet, 'awsvm')
router.register(r'awsproviders', AWSProviderViewSet)
router.register(r'awsvmconfigs', AWSVMConfigViewSet)
router.register(r'awsfirewallrule', AWSFirewallRuleViewSet, 'awsfirewallrule')
router.register(r'awsaudit', AWSAuditViewSet, 'awsaudit')
router.register(r'awspowerlog', AWSPowerLogViewSet, 'awspowerlog')

router.register(r'vmexpiration', VMExpirationViewSet, 'vmexpiration')
router.register(r'firewallruleexpiration', FirewallRuleExpirationViewSet,
        'firewallruleexpiration')
router.register(r'firewallrule', FirewallRuleViewSet, 'firewallrule')

urlpatterns = [
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
    url(r'^set-expiration$', set_expiration, name='setExpiration'),
    url(r'^create-firewall-rule$', create_firewall_rule,
        name='createFirewallRule'),
    url(r'^delete-firewall-rule$', delete_firewall_rule,
        name='deleteFirewallRule'),
] + staticfiles_urlpatterns()
