from django.conf.urls import patterns, url

from vmm import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^create/$', views.create, name='create'),
    url(r'^detail/(?P<primary_name>\w+)', views.detail, name='detail'),
    url(r'^terminate/(?P<instance_id>[\w\-]+)', views.terminate, name='terminate'),
)
