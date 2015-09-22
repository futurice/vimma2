from django.contrib.auth.models import User as DefaultUser, AbstractBaseUser, AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
import json
import logging

from vimma.haikunator import heroku
from vimma.tools import subclassmodels, get_import

class CleanModel(models.Model):
    """
    Force full_clean() on Model.save()
    https://docs.djangoproject.com/en/1.8/ref/models/instances/#validating-objects
    """

    @classmethod
    def choices(cls):
        return {k().__class__.__name__.lower():k for k in cls.implementations()}

    @classmethod
    def implementations(cls):
        return subclassmodels(cls)

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    expiration_controller_cls = ('','')
    def expiration_controller(self):
        cls = get_import(*self.expiration_controller_cls)
        return cls(parent=self)

    class Meta:
        abstract = True

class Permission(CleanModel):
    name = models.CharField(max_length=255, unique=True)

    def __str__(self):
        return self.name


class Role(CleanModel):
    name = models.CharField(max_length=255, unique=True)
    permissions = models.ManyToManyField(Permission)

    def __str__(self):
        return self.name


class Project(CleanModel):
    name = models.CharField(max_length=255)
    email = models.EmailField(null=True, blank=True)

    class Meta:
        unique_together = (('name', 'email'),)

    def __str__(self):
        return self.name

class User(AbstractUser):
    projects = models.ManyToManyField(Project, blank=True)
    roles = models.ManyToManyField(Role, blank=True)

    @property
    def auditor(self):
        cls = get_import(*('vimma.audit', 'Auditor'))
        return cls(name=__name__, obj=None, user=self)

if settings.REMOTE_USER_ENABLED:
    User._meta.get_field('password').null = True
    User._meta.get_field('password').blank = True

class TimeZone(CleanModel):
    name = models.CharField(max_length=255, unique=True)

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

class Schedule(CleanModel):
    """
    A schedule marks when the VM should be powered on or powered off.

    A 7×48 matrix with boolean values marks ON (true) or OFF (false).
    Each row is a day of the week (first row is Monday, last row is Sunday).
    Each column is a 30-min time interval. First column is [0:00, 0:30),
    second is [0:30, 1:00), last column is [23:30, 24:00).
    """
    name = models.CharField(max_length=255, unique=True)
    timezone = models.ForeignKey(TimeZone, on_delete=models.PROTECT, related_name='%(class)s_destroy_requested_vms')
    matrix = models.TextField(validators=[schedule_matrix_validator], blank=True)
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


class Provider(CleanModel):
    """
    A provider of virtual machines.

    This abstract model holds fields common across all models.
    """
    name = models.CharField(max_length=255, unique=True)
    # the maximum length of a schedule override which users may place on a VM
    max_override_seconds = models.BigIntegerField(default=0)
    # To create a VM from a Config belonging to a ‘special’ provider,
    # users need to have the Perms.USE_SPECIAL_PROVIDER permission.
    is_special = models.BooleanField(default=False)
    # flag showing which Provider is the default one, preselected in the UI
    default = models.BooleanField(default=False)

    def __str__(self):
        return '{}'.format(self.name)

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



class FirewallRule(CleanModel):
    PROTO_TCP = 'tcp'
    PROTO_UDP = 'udp'
    IP_PROTOCOL_CHOICES = (
        (PROTO_TCP, 'TCP'),
        (PROTO_UDP, 'UDP'),
    )
    ip_protocol = models.CharField(max_length=255, choices=IP_PROTOCOL_CHOICES)

    from_port = models.PositiveIntegerField()
    to_port = models.PositiveIntegerField()

    def is_special(self):
        return False

    def __str__(self):
        return '{} {}->{}'.format(self.ip_protocol.upper(), self.from_port, self.to_port)

    class Meta:
        abstract = True


class VM(CleanModel):
    config = NotImplementedError("models.ForeignKey('my.Config', on_delete=models.PROTECT, related_name='vm')")

    project = models.ForeignKey('vimma.Project', on_delete=models.PROTECT, related_name='%(app_label)s_%(class)s')
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT, related_name='%(app_label)s_%(class)s')

    audits = GenericRelation('vimma.Audit', content_type_field='object_content_type', object_id_field='object_id')

    name = models.CharField(max_length=255, blank=True)
    # A ‘schedule override’: keep ON or OFF until a timestamp
    # True → Powered ON, False → Powered OFF, None → no override
    sched_override_state = models.NullBooleanField(default=None)
    # end of schedule override, in seconds since epoch
    sched_override_tstamp = models.BigIntegerField(blank=True, null=True)
    # User-entered text about this vm

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('vimma.User', null=True, blank=True,
            on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_created_by')
    comment = models.CharField(max_length=255, blank=True)

    # When the VM status was updated from the remote provider. The status
    # fields are in the provider-specific VM submodels, but updating the status
    # is a common action for all VMs so the field is here.
    status_updated_at = models.DateTimeField(null=True, blank=True)

    # First a user requests destruction
    destroy_request_at = models.DateTimeField(blank=True, null=True)
    destroy_request_by = models.ForeignKey('vimma.User', null=True, blank=True,
            on_delete=models.SET_NULL, related_name='%(app_label)s_%(class)s_destroy_request_by')
    # When all destruction tasks succeed, mark the VM as destroyed
    destroyed_at = models.DateTimeField(blank=True, null=True)

    vm_controller_cls = ('vimma.controller,', 'VMController')
    def controller(self):
        cls = get_import(*self.vm_controller_cls)
        return cls(vm=self)

    @property
    def auditor(self):
        cls = get_import(*('vimma.audit', 'Auditor'))
        return cls(name=__name__, obj=self)

    def generate_name(self):
        return heroku()

    def save(self, *args, **kwargs):
        self.name = self.name or self.generate_name()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        abstract = True

class Config(CleanModel):
    """
    Configuration for a Provider. A provider may have several Configs.

    A config knows how to create a VM.
    """
    provider = NotImplementedError("models.ForeignKey('my.Provider', on_delete=models.PROTECT, related_name='config')")
    # The default schedule for this VM config. Users are allowed to choose this
    # schedule for VMs made from this config, even if the schedule itself
    # requires additional permissions.
    default_schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT, related_name="%(app_label)s_%(class)s")

    name = models.CharField(max_length=255, unique=True)
    # Users need Perms.USE_SPECIAL_VM_CONFIG to create a VM from this config.
    is_special = models.BooleanField(default=False)
    # flag showing which Config is the default one for its provider,
    # preselected in the UI
    default = models.BooleanField(default=False)

    def __str__(self):
        return '{}'.format(self.name)

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

    def vm_model(self):
        return self._meta.get_field('vm').related_model

    class Meta:
        abstract = True


class Expiration(CleanModel):
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

    class Meta:
        abstract = True

class Expiration(Expiration):
    expiration_controller_cls = ('vimma.expiry', 'ExpirationController')

    class Meta:
        abstract = True

class FirewallRuleExpiration(Expiration):
    expiration_controller_cls = ('vimma.expiry', 'FirewallRuleExpirationController')

    class Meta:
        abstract = True

class PowerLog(CleanModel):
    """
    The power state (ON or OFF) of a VM at a point in time.
    """
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    # True → ON, False → OFF.
    powered_on = models.BooleanField(default=False)

    def onfmt(self):
        return 'ON' if self.powered_on else 'OFF'

    def __str__(self):
        return '{} @{}: {}'.format(self.vm.name, self.timestamp.strftime('%H:%M'), self.onfmt())

    class Meta:
        abstract = True

class Audit(CleanModel):
    """
    Audit logs events for:
    - a User
    - a VM
    - <nobody in particular>
    """
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

    level = models.CharField(max_length=255, choices=LEVEL_CHOICES)
    text = models.TextField()

    user = models.ForeignKey('vimma.User', null=True, blank=True, on_delete=models.SET_NULL, related_name="%(app_label)s_%(class)s")
    project = models.ForeignKey('vimma.Project', null=True, blank=True, on_delete=models.SET_NULL, related_name="%(app_label)s_%(class)s")

    object_content_type = models.ForeignKey(ContentType, null=True, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('object_content_type', 'object_id')

    def __str__(self):
        return "%s..."%self.text[:40]

