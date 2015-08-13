from django.conf import settings
from django.db import models, transaction

import logging
import ipaddress
import re

from vimma.models import VM, VMConfig, Provider

class AWSVMConfig(VMConfig, models.Model):
    provider = models.ForeignKey('aws.AWSProvider', on_delete=models.PROTECT)

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

class AWSProvider(Provider, models.Model):
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

def aws_vm_name_validator(val):
    if not re.fullmatch('^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', val):
        raise ValidationError(('Invalid AWS VM name ‘{}’, ' +
                'must be alphanumeric and dashes (-).').format(val))

class AWSVM(VM, models.Model):
    provider = models.ForeignKey('aws.AWSProvider', on_delete=models.PROTECT)

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


class AWSFirewallRule(models.Model):
    # ip_protocol, from_port, to_port and cidr_ip correspond to
    # AWS call params.

    firewallrule = models.OneToOneField('vimma.FirewallRule', on_delete=models.CASCADE, related_name='config')

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
        net = ipaddress.IPv4Network(self.cidr_ip, strict=False)
        trusted_nets = map(lambda net: ipaddress.IPv4Network(net), settings.TRUSTED_NETWORKS)
        for trusted_net in trusted_nets:
            # if net is fully contained in a trusted_net, flag rule as non-special
            if trusted_net.overlaps(net) and trusted_net.prefixlen <= net.prefixlen:
                return False
        if net.num_addresses > 256:
            return True
        return False


