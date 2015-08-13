from django.contrib import admin

from dummy.models import (
    DummyProvider, DummyVMConfig, DummyVM,
)


for model in (
    DummyProvider, DummyVMConfig, DummyVM,
    ):
    admin.site.register(model)
