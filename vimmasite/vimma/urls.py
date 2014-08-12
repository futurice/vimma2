from django.conf.urls import patterns, url, include
from rest_framework import routers

from vimma.views import ScheduleViewSet


router = routers.DefaultRouter()
router.register(r'schedules', ScheduleViewSet)

urlpatterns = patterns('',
    url(r'^api/', include(router.urls)),
)
