from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from vmm import views

urlpatterns = patterns('',
    # Login logout placeholder functionality
    url(r'^login/$', 'django.contrib.auth.views.login', {'template_name': 'common/login.html'}, name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout_then_login', {}, name='logout'),
    #
    url(r'^admin/', include(admin.site.urls)),
    url(r'^vmm/', include('vmm.urls')),
    url(r'^$', include('vmm.urls')),
    url(r'', include('vmm.urls')),
    # Not sure if the djcelery urls are worth using or not
    #url('^tasks/', include('djcelery.urls')),
)
