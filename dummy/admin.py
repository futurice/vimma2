from django.contrib import admin

from dummy.models import (
    DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog,
)


for model in (
    DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog,
    ):
    admin.site.register(model)
