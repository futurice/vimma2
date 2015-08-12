from django.contrib.auth.models import User as DefaultUser, AbstractBaseUser, AbstractUser
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.conf import settings
import json
import logging
import re
import ipaddress


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


class DummyProvider(models.Model):
    """
    Type-specific info for a Provider of type Provider.TYPE_DUMMY.
    """
    provider = models.OneToOneField(Provider, on_delete=models.PROTECT)

    def __str__(self):
        return self.provider.name


class AWSProvider(models.Model):
    """
    Type-specific info for a Provider of type Provider.TYPE_AWS.
    """
    provider = models.OneToOneField(Provider, on_delete=models.PROTECT)
    # these must not be exposed via the API
    access_key_id = models.CharField(max_length=100, blank=True)
    access_key_secret = models.CharField(max_length=100, blank=True)
    ssh_key_name = models.CharField(max_length=50, blank=True)
    # 'example.com.'
    route_53_zone = models.CharField(max_length=100, blank=True)
    # Optional security group added to every vm, in addition to the vm's
    # individual security group.
    default_security_group_id = models.CharField(max_length=50, blank=True)
    # The ID of the VPC in which to create VMs. A random subnet will be chosen
    # at VM creation time.
    vpc_id = models.CharField(max_length=50)
    # User data (e.g. a script) provided to the AWS Instances. Python Template
    # https://docs.python.org/3/library/string.html#format-string-syntax
    # given the ‘vm’ keyword argument. E.g.:
    # """#!/usr/bin/env bash
    #   echo VM NAME {vm.awsvm.name} >/test
    #   echo region {vm.provider.awsprovider.route_53_zone} >>/test
    #   echo {{curly braces}} >>/test
    # """
    user_data = models.TextField(blank=True)

    def __str__(self):
        return '{} ({})'.format(self.provider.name, self.route_53_zone)


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

    regions = sorted([
        'ap-northeast-1',
        'ap-southeast-1',
        'ap-southeast-2',
        'cn-north-1',
        'eu-central-1',
        'eu-west-1',
        'sa-east-1',
        'us-east-1',
        'us-gov-west-1',
        'us-west-1'
        'us-west-2',
    ])
    REGION_CHOICES = ((r, r) for r in regions)
    region = models.CharField(max_length=20, choices=REGION_CHOICES)

    # Amazon Machine Image ID
    ami_id = models.CharField(max_length=50, blank=True)
    instance_type = models.CharField(max_length=50, blank=True)

    # The default root device size in GB for VMs made from this config.
    root_device_size = models.IntegerField()

    # Not including ‘io1’ for now because ‘The parameter iops must be specified
    # for io1 volumes’.
    VOLUME_TYPE_CHOICES = (
        ('standard', 'Magnetic'),
        ('gp2', 'SSD'),
    )
    root_device_volume_type = models.CharField(max_length=20,
            choices=VOLUME_TYPE_CHOICES, default=VOLUME_TYPE_CHOICES[0][0])

    def __str__(self):
        return '{}, {} ({})'.format(self.ami_id, self.instance_type,
                self.vmconfig.name)


class VM(models.Model):
    """
    A virtual machine. This model holds only the data common for all VMs from
    any provider. Additional data specific to the provider's type is in a model
    linked via a one-to-one field.
    """
    provider = models.ForeignKey(Provider, on_delete=models.PROTECT)
    project = models.ForeignKey(Project, on_delete=models.PROTECT)
    schedule = models.ForeignKey(Schedule, on_delete=models.PROTECT)
    expiration = models.ForeignKey(VMExpiration, on_delete=models.CASCADE, null=True, blank=True)

    # A ‘schedule override’: keep ON or OFF until a timestamp
    # True → Powered ON, False → Powered OFF, None → no override
    sched_override_state = models.NullBooleanField(default=None)
    # end of schedule override, in seconds since epoch
    sched_override_tstamp = models.BigIntegerField(blank=True, null=True)
    # User-entered text about this vm

    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, null=True, blank=True,
            on_delete=models.SET_NULL, related_name='created_vms')
    comment = models.CharField(max_length=200, blank=True)

    # When the VM status was updated from the remote provider. The status
    # fields are in the provider-specific VM submodels, but updating the status
    # is a common action for all VMs so the field is here.
    status_updated_at = models.DateTimeField(null=True, blank=True)

    # First a user requests destruction
    destroy_request_at = models.DateTimeField(blank=True, null=True)
    destroy_request_by = models.ForeignKey(User, null=True, blank=True,
            on_delete=models.SET_NULL, related_name='destroy_requested_vms')
    # When all destruction tasks succeed, mark the VM as destroyed
    destroyed_at = models.DateTimeField(blank=True, null=True)


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


def aws_vm_name_validator(val):
    if not re.fullmatch('^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', val):
        raise ValidationError(('Invalid AWS VM name ‘{}’, ' +
                'must be alphanumeric and dashes (-).').format(val))


class AWSVM(models.Model):
    """
    Type-specific data for a VM of type Provider.TYPE_AWS.
    """
    vm = models.OneToOneField(VM, on_delete=models.PROTECT)
    # Free-form text, shown to the user. Stores the VM state reported by AWS.
    # Synced regularly by the update tasks.
    state = models.CharField(max_length=100, blank=True)
    # AWS fields:
    name = models.CharField(max_length=50, validators=[aws_vm_name_validator])
    region = models.CharField(max_length=20)
    security_group_id = models.CharField(max_length=50, blank=True)
    reservation_id = models.CharField(max_length=50, blank=True)
    instance_id = models.CharField(max_length=50, blank=True)
    # public IP address
    ip_address = models.CharField(max_length=50, blank=True)
    private_ip_address = models.CharField(max_length=50, blank=True)

    # Destruction happens using several asynchronous tasks, which mark these
    # fields when they succeed. When all fields are True we can mark the parent
    # .vm model as destroyed.
    instance_terminated = models.BooleanField(default=False)
    security_group_deleted = models.BooleanField(default=False)


class FirewallRule(models.Model):
    """
    The base model for all firewall rules, with type-specific submodels.
    """
    vm = models.ForeignKey(VM, on_delete=models.CASCADE)
    expiration = models.ForeignKey(FirewallRuleExpiration, on_delete=models.CASCADE, null=True, blank=True)

    def is_special(self):
        """
        Whether this rule is special (i.e. not regular).

        This method should be called inside a transaction (for ACID behavior).
        """
        t = self.vm.provider.type
        if t == Provider.TYPE_AWS:
            return self.awsfirewallrule.is_special()
        else:
            # unknown provider type
            return True


class AWSFirewallRule(models.Model):
    """
    AWS Firewall Rule.
    """
    firewallrule = models.OneToOneField(FirewallRule, on_delete=models.CASCADE)

    # ip_protocol, from_port, to_port and cidr_ip correspond to
    # AWS call params.

    PROTO_TCP = 'tcp'
    PROTO_UDP = 'udp'
    IP_PROTOCOL_CHOICES = (
        (PROTO_TCP, 'TCP'),
        (PROTO_UDP, 'UDP'),
    )
    ip_protocol = models.CharField(max_length=10, choices=IP_PROTOCOL_CHOICES)

    from_port = models.PositiveIntegerField()
    to_port = models.PositiveIntegerField()
    cidr_ip = models.CharField(max_length=50)

    def is_special(self):
        """
        Same as FirewallRule.is_special.
        """
        net = ipaddress.IPv4Network(self.cidr_ip, strict=False)
        trusted_nets = map(lambda net: ipaddress.IPv4Network(net), settings.TRUSTED_NETWORKS)
        for trusted_net in trusted_nets:
            # if net is fully contained in a trusted_net, flag rule as non-special
            if trusted_net.overlaps(net) and trusted_net.prefixlen <= net.prefixlen:
                return False
        if net.num_addresses > 256:
            return True
        return False

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
    user = models.ForeignKey(User, null=True, blank=True,
            on_delete=models.SET_NULL)
    vm = models.ForeignKey(VM, null=True, blank=True,
            on_delete=models.SET_NULL)


class PowerLog(models.Model):
    """
    The power state (ON or OFF) of a VM at a point in time.

    If you're not sure what the vm's state is (e.g. you encountered an error
    while checking it) don't create a PowerLog object.
    """
    vm = models.ForeignKey(VM, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    # True → ON, False → OFF. Can't be None, so the value must be explicit.
    powered_on = models.BooleanField(default=None)
