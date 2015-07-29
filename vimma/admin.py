from django.contrib import admin

from vimma.models import (
    TimeZone, Permission,
    Role, User, Project,
    Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
)


for model in (
        TimeZone, Permission,
        Role, User, Project,
        Provider, DummyProvider, AWSProvider,
        VMConfig, DummyVMConfig, AWSVMConfig,
        ):
    admin.site.register(model)
