from django.db import models, transaction

from vimma.models import VM, VMConfig, Provider, Audit, PowerLog, FirewallRule, FirewallRuleExpiration, VMExpiration

class DummyVM(VM):
    vm_controller_cls = ('dummy.controller', 'DummyVMController')

    config = models.ForeignKey('dummy.DummyVMConfig', on_delete=models.PROTECT, related_name="vm")
    firewallrules = models.ManyToManyField('dummy.DummyFirewallRule', blank=True)

    name = models.CharField(max_length=50)
    # Free-form text, meant to be read by the user. Simulates Vimma's local
    # copy of the remote machine state, synced regularly by the update tasks.
    status = models.CharField(max_length=50, blank=True)

    # these fields simulate the machine state, managed remotely by the Provider
    destroyed = models.BooleanField(default=False)
    poweredon = models.BooleanField(default=False)

    def isOn(self, state=None):
        return self.poweredon

class DummyProvider(Provider):
    pass

class DummyVMConfig(VMConfig):
    vm_model = DummyVM
    provider = models.ForeignKey('dummy.DummyProvider', on_delete=models.PROTECT, related_name="config")

class DummyFirewallRule(FirewallRule, models.Model):
    pass

class DummyFirewallRuleExpiration(FirewallRuleExpiration, models.Model):
    firewallrule = models.OneToOneField('dummy.DummyFirewallRule', related_name="expiration")

class DummyVMExpiration(VMExpiration):
    vm = models.OneToOneField('dummy.DummyVM', related_name="expiration")

class DummyAudit(Audit, models.Model):
    vm = models.ForeignKey('dummy.DummyVM', related_name="audit")

class DummyPowerLog(PowerLog, models.Model):
    vm = models.ForeignKey('dummy.DummyVM', related_name="powerlog")
