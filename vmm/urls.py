from django.conf.urls import patterns, url

from vmm import views

urlpatterns = patterns('',
    # Generic views
    url(r'^$', views.index, name='index'),
    url(r'^detail/(?P<primary_name>\w+)', views.detail, name='detail'),
    # Creation, termination etc
    url(r'^create/$', views.create, name='create'),
    url(r'^terminate/(?P<instance_id>[\w\-]+)', views.terminate, name='terminate'),
    # Ajax views
    url(r'^vmstatus/$', views.vmstatus, name='vmstatus'),
    url(r'^vmstatus/(?P<primary_name>[\w\-]+)', views.vmstatus, name='vmstatus'),
)
