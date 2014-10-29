from django.contrib import admin

from vimma.models import (
    Provider, DummyProvider, AWSProvider,
)


admin.site.register(Provider)
admin.site.register(DummyProvider)
admin.site.register(AWSProvider)
