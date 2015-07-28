from django.conf.urls import url, include
from rest_framework import routers

from vimma.views import (
    UserViewSet,
    TimeZoneViewSet, ScheduleViewSet, ProjectViewSet,
    ProviderViewSet, DummyProviderViewSet, AWSProviderViewSet,
    VMConfigViewSet, DummyVMConfigViewSet, AWSVMConfigViewSet,
    VMViewSet, DummyVMViewSet, AWSVMViewSet,
    FirewallRuleViewSet, AWSFirewallRuleViewSet,
    AuditViewSet, PowerLogViewSet, ExpirationViewSet, VMExpirationViewSet,
    FirewallRuleExpirationViewSet,
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
router.register(r'providers', ProviderViewSet)
router.register(r'dummyproviders', DummyProviderViewSet)
router.register(r'awsproviders', AWSProviderViewSet)
router.register(r'vmconfigs', VMConfigViewSet, 'vmconfig')
router.register(r'dummyvmconfigs', DummyVMConfigViewSet)
router.register(r'awsvmconfigs', AWSVMConfigViewSet)
router.register(r'vms', VMViewSet, 'vm')
router.register(r'dummyvms', DummyVMViewSet, 'dummyvm')
router.register(r'awsvm', AWSVMViewSet, 'awsvm')
router.register(r'audit', AuditViewSet, 'audit')
router.register(r'powerlog', PowerLogViewSet, 'powerlog')
router.register(r'expiration', ExpirationViewSet, 'expiration')
router.register(r'vmexpiration', VMExpirationViewSet, 'vmexpiration')
router.register(r'firewallruleexpiration', FirewallRuleExpirationViewSet,
        'firewallruleexpiration')
router.register(r'firewallrule', FirewallRuleViewSet, 'firewallrule')
router.register(r'awsfirewallrule', AWSFirewallRuleViewSet, 'awsfirewallrule')

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
]
