from django.contrib import admin

from vimma.models import (
    Role,
    Provider, DummyProvider, AWSProvider,
    VMConfig, DummyVMConfig, AWSVMConfig,
)


for model in (
        Role,
        Provider, DummyProvider, AWSProvider,
        VMConfig, DummyVMConfig, AWSVMConfig,
        ):
    admin.site.register(model)
