from django.conf.urls import patterns, url, include
from rest_framework import routers

from vimma.views import TimeZoneViewSet, ScheduleViewSet, index, test


router = routers.DefaultRouter()
router.register(r'timezones', TimeZoneViewSet)
router.register(r'schedules', ScheduleViewSet)

urlpatterns = patterns('',
    url(r'^api/', include(router.urls)),
    url(r'^$', index, name='index'),
    url(r'^test$', test, name='test'),
)
