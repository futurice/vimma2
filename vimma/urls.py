from django.conf import settings
from django.conf.urls import url, include
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from rest_framework import routers

from vimma.tools import get_classes

from vimma.viewsets import (
    UserViewSet,
    TimeZoneViewSet,
    ScheduleViewSet,
    ProjectViewSet,
)
from vimma.views import (
    index, base_js, test,
)

dummy_viewsets = get_classes('dummy.viewsets', 'ViewSet')
aws_viewsets = get_classes('aws.viewsets', 'ViewSet')

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'timezones', TimeZoneViewSet)
router.register(r'schedules', ScheduleViewSet)
router.register(r'projects', ProjectViewSet, 'project')

def register_viewsets(namespace, viewsets):
    for vs in viewsets:
        model_name = vs.serializer_class.Meta.model._meta.model_name
        router.register(r'%s/%s'%(namespace,model_name), vs, '%s%s'%(namespace,model_name))

register_viewsets('dummy', dummy_viewsets)
register_viewsets('aws', aws_viewsets)

urlpatterns = [
    url(r'^api/', include(router.urls)),

    url(r'^$', index, name='index'),
    url(r'^base.js$', base_js, name='base_js'),
    url(r'^test$', test, name='test'),

] + staticfiles_urlpatterns()
