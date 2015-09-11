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

] + staticfiles_urlpatterns()
