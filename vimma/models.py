from django.contrib.auth.models import User as DefaultUser, AbstractBaseUser, AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.conf import settings
import json
import logging

class Permission(models.Model):
    """
    A Permission.

    There is a special omnipotent permission used to grant all permissions.
    """
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Role(models.Model):
    """
    A role represents a set of Permissions.

    A user is assigned a set of Roles and has all permissions in those roles.
    """
    name = models.CharField(max_length=100, unique=True)
    permissions = models.ManyToManyField(Permission)

    def __str__(self):
        return self.name


class Project(models.Model):
    """
    Projects group Users and VMs.
    """
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField()

    def __str__(self):
        return self.name

class User(AbstractUser):
    projects = models.ManyToManyField(Project, blank=True)
    roles = models.ManyToManyField(Role, blank=True)

if settings.REMOTE_USER_ENABLED:
    User._meta.get_field('password').null = True
    User._meta.get_field('password').blank = True

class TimeZone(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


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
    # ‘special’ schedules can't be used by everyone. E.g. 24h turned on.
    # Users need the USE_SPECIAL_SCHEDULE permission to use them.
    is_special = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    def default_matrix(self):
        return [[False]*48]*7

    def save(self, *args, **kwargs):
        if not self.matrix:
            self.matrix = json.dumps(self.default_matrix())
        super().save(*args, **kwargs)


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
    # the maximum length of a schedule override which users may place on a VM
    max_override_seconds = models.BigIntegerField(default=0)
    # To create a VM from a Config belonging to a ‘special’ provider,
    # users need to have the Perms.USE_SPECIAL_PROVIDER permission.
    is_special = models.BooleanField(default=False)
    # flag showing which Provider is the default one, preselected in the UI
    default = models.BooleanField(default=False)

    def __str__(self):
        return '{} ({})'.format(self.name, self.get_type_display())

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.default:
                (self.__class__.objects.filter().exclude(id=self.id)
                        .update(default=False))
            elif (not self.__class__.objects.filter(default=True)
                    .exclude(id=self.id).exists()):
                self.default = True
            super().save(*args, **kwargs)

    class Meta:
        abstract = True


class VMConfig(models.Model):
    """
    A VM Configuration for a Provider. A provider may have several of these.

    This model holds fields common across all VM Configs. Additional data
    specific to the provider's type is in a model linked via a one-to-one
    field.
    """
    provider = "PARENT IMPLEMENTS: models.ForeignKey(Provider, on_delete=models.PROTECT)"
    # The default schedule for this VM config. Users are allowed to choose this
    # schedule for VMs made from this config, even if the schedule itself
    # requires additional permissions.
    default_schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT)

    name = models.CharField(max_length=50, unique=True)
    # Users need Perms.USE_SPECIAL_VM_CONFIG to create a VM from this config.
    is_special = models.BooleanField(default=False)
    # flag showing which VMConfig is the default one for its provider,
    # preselected in the UI
    default = models.BooleanField(default=False)

    def __str__(self):
        return '{} ({})'.format(self.name, self.provider.name)

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.default:
                (self.__class__.objects.filter(provider=self.provider)
                        .exclude(id=self.id)
                        .update(default=False))
            elif (not self.__class__.objects
                    .filter(provider=self.provider, default=True)
                    .exclude(id=self.id).exists()):
                self.default = True
            super().save(*args, **kwargs)

    class Meta:
        abstract = True


class FirewallRule(models.Model):
    expiration = models.OneToOneField('vimma.FirewallRuleExpiration', on_delete=models.CASCADE)

    def is_special(self):
        return False


class VM(models.Model):
    """
    A virtual machine. This model holds only the data common for all VMs from
    any provider.
    """
    provider = "PARENT IMPLEMENTS models.ForeignKey(Provider, on_delete=models.PROTECT)"
    project = models.ForeignKey('vimma.Project', on_delete=models.PROTECT)
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT)
    audit = models.ForeignKey('vimma.Audit', on_delete=models.CASCADE, null=True, blank=True)
    expiration = models.OneToOneField('vimma.VMExpiration', on_delete=models.CASCADE, null=True, blank=True)
    firewallrules = models.ManyToManyField('vimma.FirewallRule', blank=True)

    # A ‘schedule override’: keep ON or OFF until a timestamp
    # True → Powered ON, False → Powered OFF, None → no override
    sched_override_state = models.NullBooleanField(default=None)
    # end of schedule override, in seconds since epoch
    sched_override_tstamp = models.BigIntegerField(blank=True, null=True)
    # User-entered text about this vm

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('vimma.User', null=True, blank=True,
            on_delete=models.SET_NULL, related_name='%(class)s_created_vms')
    comment = models.CharField(max_length=200, blank=True)

    # When the VM status was updated from the remote provider. The status
    # fields are in the provider-specific VM submodels, but updating the status
    # is a common action for all VMs so the field is here.
    status_updated_at = models.DateTimeField(null=True, blank=True)

    # First a user requests destruction
    destroy_request_at = models.DateTimeField(blank=True, null=True)
    destroy_request_by = models.ForeignKey('vimma.User', null=True, blank=True,
            on_delete=models.SET_NULL, related_name='%(class)s_destroy_requested_vms')
    # When all destruction tasks succeed, mark the VM as destroyed
    destroyed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True


class PowerLog(models.Model):
    """
    The power state (ON or OFF) of a VM at a point in time.

    If you're not sure what the vm's state is (e.g. you encountered an error
    while checking it) don't create a PowerLog object.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    # True → ON, False → OFF. Can't be None, so the value must be explicit.
    powered_on = models.BooleanField(default=None)


class Expiration(models.Model):
    """
    An item that expires.

    At certain intervals (before and after the expiration date) notifications
    are sent. It stores when the latest one was sent.
    There is a grace period after the expiration date, then a ‘grace end’
    action is performed. It stores whether this ran.
    ExpirationController implements the features.
    """
    expires_at = models.DateTimeField()
    # when the most recent notification was sent
    last_notification = models.DateTimeField(blank=True, null=True)
    grace_end_action_performed = models.BooleanField(default=False)

    @classmethod
    def implementations(cls):
        return Expiration.__subclasses__()

    class Meta:
        abstract = True

class VMExpiration(Expiration):
    controller = ('vimma.expiry', 'VMExpirationController')

class FirewallRuleExpiration(Expiration):
    controller = ('vimma.expiry', 'FirewallRuleExpirationController')

class Audit(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # Imitating https://docs.python.org/3/library/logging.html#logging-levels
    # Sorting level names lexicographically to query by min_level in the API.
    DEBUG = '1-DEBUG'
    INFO = '2-INFO'
    WARNING = '3-WARNING'
    ERROR = '4-ERROR'
    LEVEL_CHOICES = (
        (DEBUG, 'DEBUG'),
        (INFO, 'INFO'),
        (WARNING, 'WARNING'),
        (ERROR, 'ERROR'),
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
    user = models.ForeignKey('vimma.User', null=True, blank=True,
            on_delete=models.SET_NULL)


