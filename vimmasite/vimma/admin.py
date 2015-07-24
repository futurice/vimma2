from django.contrib import admin

from vimma.models import (
    TimeZone,
    Role, User,
    Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
)


for model in (
        TimeZone,
        Role, User,
        Provider, DummyProvider, AWSProvider,
        VMConfig, DummyVMConfig, AWSVMConfig,
        ):
    admin.site.register(model)
