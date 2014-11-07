from django.contrib import admin

from vimma.models import (
    Role,
    Provider, DummyProvider, AWSProvider,
)


admin.site.register(Role)
admin.site.register(Provider)
admin.site.register(DummyProvider)
admin.site.register(AWSProvider)
