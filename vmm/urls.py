from django.conf.urls import patterns, url

from vmm import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^detail/(?P<primary_name>\w+)', views.detail, name='detail'),
    url(r'^create/(?P<virtualmachine_id>\w+)$', views.create, name='create'),
)
