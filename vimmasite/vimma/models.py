from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
import json
import logging


class Permission(models.Model):
    """
    A Permission.

    There is a special omnipotent permission used to grant all permissions.
    """
    name = models.CharField(max_length=100, unique=True)


class Role(models.Model):
    """
    A role represents a set of Permissions.

    A user is assigned a set of Roles and has all permissions in those roles.
    """
    name = models.CharField(max_length=20, unique=True)
    permissions = models.ManyToManyField(Permission)


class Project(models.Model):
    """
    Projects group Users and VMs.
    """
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField()


class Profile(models.Model):
    """
    An extension of the User model.
    """
    user = models.OneToOneField(User)
    projects = models.ManyToManyField(Project)
    roles = models.ManyToManyField(Role)


class TimeZone(models.Model):
    name = models.CharField(max_length=100, unique=True)


def schedule_matrix_validator(val):
    try:
        matrix = json.loads(val)
    except ValueError as e:
        raise ValidationError(e.args[0] if e.args else "Invalid JSON")
    if len(matrix) != 7:
        raise ValidationError('Schedule matrix has ' + str(len(matrix)) +
                ' rows instead of 7')
    for row in matrix:
        if len(row) != 48:
            raise ValidationError('Schedule matrix row has ' + str(len(row)) +
                    ' items instead of 48')
        for item in row:
            if type(item) != bool:
                raise ValidationError('Schedule matrix has non-bool element ' +
                        str(type(item)))

class Schedule(models.Model):
    """
    A schedule marks when the VM should be powered on or powered off.

    A 7×48 matrix with boolean values marks ON (true) or OFF (false).
    Each row is a day of the week (first row is Monday, last row is Sunday).
    Each column is a 30-min time interval. First column is [0:00, 0:30),
    second is [0:30, 1:00), last column is [23:30, 24:00).
    """
    name = models.CharField(max_length=50, unique=True)
    timezone = models.ForeignKey(TimeZone, on_delete=models.PROTECT)
    matrix = models.TextField(validators=[schedule_matrix_validator])
    # ‘special’ schedules can't be used by anyone. E.g. 24h turned on.
    # Users need the USE_SPECIAL_SCHEDULE permission to use them.
    is_special = models.BooleanField(default=False)


class Provider(models.Model):
    """
    A provider of virtual machines.

    This model holds fields common across all models. Additional data specific
    to this provider's type (e.g. Amazon Web Services) is held in a linked
    model via a one-to-one field.

    E.g. each account at Amazon Web Services is a different Provider.
    """
    TYPE_DUMMY = 'dummy'
    TYPE_AWS = 'aws'
    TYPE_CHOICES = (
        (TYPE_DUMMY, 'Dummy'),
        (TYPE_AWS, 'Amazon Web Services'),
    )
    name = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)


class DummyProvider(models.Model):
    """
    Type-specific info for a Provider of type Provider.TYPE_DUMMY.
    """
    provider = models.OneToOneField(Provider, on_delete=models.PROTECT)


class AWSProvider(models.Model):
    """
    Type-specific info for a Provider of type Provider.TYPE_AWS.
    """
    provider = models.OneToOneField(Provider, on_delete=models.PROTECT)
    # these must not be exposed via the API
    access_key_id = models.CharField(max_length=100, blank=True)
    access_key_secret = models.CharField(max_length=100, blank=True)


class VMConfig(models.Model):
    """
    A VM Configuration for a Provider. A provider may have several of these.

    This model holds fields common across all VM Configs. Additional data
    specific to the provider's type is in a model linked via a one-to-one
    field.
    """
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    name = models.CharField(max_length=50, unique=True)
    # The default schedule for this VM config. Users are allowed to choose this
    # schedule for VMs made from this config, even if the schedule itself
    # requires additional permissions.
    default_schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT)
    # Users need Perms.VM_CONF_INSTANTIATE to create a VM from this config.
    requires_permission = models.BooleanField(default=False)


class DummyVMConfig(models.Model):
    """
    Type-specific info for a VMConfig of type Provider.TYPE_DUMMY.
    """
    vmconfig = models.OneToOneField(VMConfig, on_delete=models.PROTECT)


class AWSVMConfig(models.Model):
    """
    Type-specific info for a VMConfig of type Provider.TYPE_AWS.
    """
    vmconfig = models.OneToOneField(VMConfig, on_delete=models.PROTECT)
    # Amazon Machine Image ID
    ami_id = models.CharField(max_length=50, blank=True)
    instance_type = models.CharField(max_length=50, blank=True)


class VM(models.Model):
    """
    A virtual machine. This model holds only the data common for all VMs from
    any provider. Additional data specific to the provider's type is in a model
    linked via a one-to-one field.
    """
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT)


class DummyVM(models.Model):
    """
    Type-specific data for a VM of type Provider.TYPE_DUMMY.
    """
    vm = models.OneToOneField(VM, on_delete=models.PROTECT)
    name = models.CharField(max_length=50)

    # Free-form text, meant to be read by the user. Simulates Vimma's local
    # copy of the remote machine state, synced regularly by the update tasks.
    status = models.CharField(max_length=50, blank=True)

    # these fields simulate the machine state, managed remotely by the Provider
    destroyed = models.BooleanField(default=False)
    poweredon = models.BooleanField(default=False)


class AWSVM(models.Model):
    """
    Type-specific data for a VM of type Provider.TYPE_AWS.
    """
    vm = models.OneToOneField(VM, on_delete=models.PROTECT)
    # Free-form text, shown to the user. Stores the VM state reported by AWS.
    # Synced regularly by the update tasks.
    state = models.CharField(max_length=100, blank=True)
    # AWS fields:
    name_tag = models.CharField(max_length=50)
    region = models.CharField(max_length=20)
    security_group_id = models.CharField(max_length=50, blank=True)
    reservation_id = models.CharField(max_length=50, blank=True)
    instance_id = models.CharField(max_length=50, blank=True)


class Audit(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)

    # Imitating https://docs.python.org/3/library/logging.html#logging-levels
    DEBUG = 'DEBUG'
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    LEVEL_CHOICES = (
        (DEBUG, DEBUG),
        (INFO, INFO),
        (WARNING, WARNING),
        (ERROR, ERROR),
    )
    # corresponding logging.X level from the standard library
    STD_LEVEL = {
        DEBUG: logging.DEBUG,
        INFO: logging.INFO,
        WARNING: logging.WARNING,
        ERROR: logging.ERROR,
    }
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)

    # Constant used outside this class, e.g. to trim longer text before
    # creating an Audit object.
    TEXT_MAX_LENGTH=4096
    text = models.CharField(max_length=TEXT_MAX_LENGTH)

    # Objects this audit message is related to, if any
    user = models.ForeignKey(User, null=True, blank=True,
            on_delete=models.SET_NULL)
    vm = models.ForeignKey(VM, null=True, blank=True,
            on_delete=models.SET_NULL)
