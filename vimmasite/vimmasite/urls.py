from django.conf.urls import include, url
from django.contrib import admin

import vimma.urls

urlpatterns = [
    # Examples:
    # url(r'^$', 'vimmasite.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),

    url(r'^admin/', include(admin.site.urls)),
    url(r'^vimma/', include(vimma.urls)),
]
