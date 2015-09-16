from django.db import models, transaction

import vimma.models

class VM(vimma.models.VM):
    vm_controller_cls = ('dummy.controller', 'VMController')

    config = models.ForeignKey('dummy.Config', on_delete=models.PROTECT, related_name="vm")

    # Free-form text, meant to be read by the user. Simulates Vimma's local
    # copy of the remote machine state, synced regularly by the update tasks.
    status = models.CharField(max_length=255, blank=True)

    # these fields simulate the machine state, managed remotely by the Provider
    destroyed = models.BooleanField(default=False)
    poweredon = models.BooleanField(default=False)

    def isOn(self, state=None):
        return self.poweredon

class Provider(vimma.models.Provider):
    pass

class Config(vimma.models.Config):
    vm_model = VM
    provider = models.ForeignKey('dummy.Provider', on_delete=models.PROTECT, related_name="config")

class FirewallRule(vimma.models.FirewallRule, models.Model):
    vm = models.ForeignKey('dummy.VM', related_name="firewallrule")

class FirewallRuleExpiration(vimma.models.FirewallRuleExpiration, models.Model):
    firewallrule = models.OneToOneField('dummy.FirewallRule', related_name="expiration")

class Expiration(vimma.models.Expiration):
    vm = models.OneToOneField('dummy.VM', related_name="expiration")

class PowerLog(vimma.models.PowerLog, models.Model):
    vm = models.ForeignKey('dummy.VM', related_name="powerlog")
