from django.db import models, transaction

from vimma.models import VM, VMConfig, Provider, Audit, PowerLog, FirewallRule, FirewallRuleExpiration, VMExpiration

class DummyProvider(Provider):
    pass

class DummyVM(VM):
    config = models.ForeignKey('dummy.DummyVMConfig', on_delete=models.PROTECT, related_name="vm")
    firewallrules = models.ManyToManyField('dummy.DummyFirewallRule', blank=True)
    expiration = models.OneToOneField('dummy.DummyVMExpiration', on_delete=models.CASCADE, null=True, blank=True)

    name = models.CharField(max_length=50)
    # Free-form text, meant to be read by the user. Simulates Vimma's local
    # copy of the remote machine state, synced regularly by the update tasks.
    status = models.CharField(max_length=50, blank=True)

    # these fields simulate the machine state, managed remotely by the Provider
    destroyed = models.BooleanField(default=False)
    poweredon = models.BooleanField(default=False)

    def isOn(self, state=None):
        return self.poweredon

    def controller(self):
        from dummy.controller import DummyVMController
        return DummyVMController(vm=self)

class DummyFirewallRule(FirewallRule, models.Model):
    expiration = models.ForeignKey('dummy.DummyFirewallRuleExpiration', on_delete=models.CASCADE, related_name="firewallrule")

class DummyFirewallRuleExpiration(FirewallRuleExpiration, models.Model):
    pass

class DummyVMConfig(VMConfig):
    vm_model = DummyVM
    provider = models.ForeignKey('dummy.DummyProvider', on_delete=models.PROTECT, related_name="config")

class DummyVMExpiration(VMExpiration):
    pass

class DummyAudit(Audit, models.Model):
    vm = models.ForeignKey('dummy.DummyVM', related_name="audit")

class DummyPowerLog(PowerLog, models.Model):
    vm = models.ForeignKey('dummy.DummyVM', related_name="powerlog")
