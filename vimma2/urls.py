from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

from vmm import views

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'vimma2.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^vmm/', include('vmm.urls')),
    url(r'^$', include('vmm.urls')),
    url(r'', include('vmm.urls')),
)

