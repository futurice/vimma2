from django.db import models, transaction

class DummyProvider(models.Model):
    """
    Type-specific info for a Provider of type Provider.TYPE_DUMMY.
    """
    provider = models.OneToOneField('vimma.Provider', on_delete=models.PROTECT)

    def __str__(self):
        return self.provider.name


class DummyVMConfig(models.Model):
    """
    Type-specific info for a VMConfig of type Provider.TYPE_DUMMY.
    """
    vmconfig = models.OneToOneField('vimma.VMConfig', on_delete=models.PROTECT)


class DummyVM(models.Model):
    """
    Type-specific data for a VM of type Provider.TYPE_DUMMY.
    """
    vm = models.OneToOneField('vimma.VM', on_delete=models.PROTECT)

    name = models.CharField(max_length=50)

    # Free-form text, meant to be read by the user. Simulates Vimma's local
    # copy of the remote machine state, synced regularly by the update tasks.
    status = models.CharField(max_length=50, blank=True)

    # these fields simulate the machine state, managed remotely by the Provider
    destroyed = models.BooleanField(default=False)
    poweredon = models.BooleanField(default=False)
