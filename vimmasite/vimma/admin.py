from django.contrib import admin

from vimma.models import (
    TimeZone,
    Profile, Role,
    Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
)


for model in (
        TimeZone,
        Profile, Role,
        Provider, DummyProvider, AWSProvider,
        VMConfig, DummyVMConfig, AWSVMConfig,
        ):
    admin.site.register(model)
