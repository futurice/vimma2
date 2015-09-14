from django.contrib import admin

from dummy.models import (
    DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog, DummyVMExpiration, DummyFirewallRule, DummyFirewallRuleExpiration
)


for model in (
    DummyProvider, DummyVMConfig, DummyVM, DummyAudit, DummyPowerLog, DummyVMExpiration, DummyFirewallRule, DummyFirewallRuleExpiration
    ):
    admin.site.register(model)
