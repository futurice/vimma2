from django.conf import settings
from django.db import models, transaction
from django.core.exceptions import ValidationError

import logging
import ipaddress
import re

import vimma.models

def aws_vm_name_validator(val):
    if not re.fullmatch('^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$', val):
        raise ValidationError({'name':'Must be alphanumeric and dashes (-).'.format(val)})

class VM(vimma.models.VM, models.Model):
    vm_controller_cls = ('aws.controller', 'VMController')

    config = models.ForeignKey('aws.Config', on_delete=models.PROTECT, related_name="vm")

    # Free-form text, shown to the user. Stores the VM state reported by .
    # Synced regularly by the update tasks.
    state = models.CharField(max_length=100, blank=True)
    #  fields:
    region = models.CharField(max_length=20, default=settings.EC2_DEFAULT_REGION)
    security_group_id = models.CharField(max_length=50, blank=True)
    reservation_id = models.CharField(max_length=50, blank=True)
    instance_id = models.CharField(max_length=50, blank=True)
    # public IP address
    ip_address = models.CharField(max_length=50, blank=True)
    private_ip_address = models.CharField(max_length=50, blank=True)

    # Destruction happens using several asynchronous tasks, which mark these
    # fields when they succeed. When all fields are True we can mark the model as destroyed.
    instance_terminated = models.BooleanField(default=False)
    security_group_deleted = models.BooleanField(default=False)

    def clean(self):
        aws_vm_name_validator(self.name)

    def isOn(self, state=None):
        new_state = state or self.state
        on_states = {'pending', 'running', 'stopping', 'shutting-down'}
        off_states = {'stopped', 'terminated'}
        powered_on = (True if new_state in on_states
                else False if new_state in off_states
                else None)
        return powered_on

class Provider(vimma.models.Provider):
    # names of environment variables for actual lookups
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
    vpc_id = models.CharField(max_length=50, null=True, blank=True)
    # User data (e.g. a script) provided to the  Instances. Python Template
    # https://docs.python.org/3/library/string.html#format-string-syntax
    # given the ‘vm’ keyword argument. E.g.:
    # """#!/usr/bin/env bash
    #   echo VM NAME {vm.awsvm.name} >/test
    #   echo region {vm.provider.awsprovider.route_53_zone} >>/test
    #   echo {{curly braces}} >>/test
    # """
    user_data = models.TextField(blank=True)

    def __str__(self):
        return '{} ({})'.format(self.name, self.route_53_zone)

class Config(vimma.models.Config, models.Model):
    vm_model = VM
    provider = models.ForeignKey('aws.Provider', on_delete=models.PROTECT, related_name="config")

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
    DEFAULT_REGION = 'us-east-1'
    region = models.CharField(max_length=20, default=DEFAULT_REGION, choices=REGION_CHOICES)

    # Amazon Machine Image ID
    ami_id = models.CharField(max_length=50, blank=True)
    instance_type = models.CharField(max_length=50, blank=True)

    # The default root device size in GB for VMs made from this config.
    AMI_DEFAULT_SIZE = 8
    root_device_size = models.IntegerField(default=AMI_DEFAULT_SIZE)

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
                self.name)


class FirewallRule(vimma.models.FirewallRule, models.Model):
    vm = models.ForeignKey('aws.VM', related_name="firewallrule")

    # ip_protocol, from_port, to_port and cidr_ip correspond to   call params.
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

    def __str__(self):
        return '{} {}->{} @{} (VM: {})'.format(self.ip_protocol.upper(), self.from_port, self.to_port, self.cidr_ip, self.vm_id)

class FirewallRuleExpiration(vimma.models.FirewallRuleExpiration, models.Model):
    firewallrule = models.OneToOneField('aws.FirewallRule', related_name="expiration")

    def __str__(self):
        return '{} for {}'.format(self.expires_at, self.firewallrule)

class Expiration(vimma.models.Expiration):
    vm = models.OneToOneField('aws.VM', related_name="expiration")

class Audit(vimma.models.Audit, models.Model):
    vm = models.ForeignKey('aws.VM', related_name="audit")

class PowerLog(vimma.models.PowerLog, models.Model):
    vm = models.ForeignKey('aws.VM', related_name="powerlog")
