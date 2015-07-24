from django.conf.urls import include, url
from django.contrib import admin

import vimma.urls

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^vimma/', include(vimma.urls)),
]
