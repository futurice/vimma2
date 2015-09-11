from django.conf import settings
from django.db import transaction
from django.utils.timezone import utc

import boto.ec2, boto.route53, boto.vpc, os
import celery.exceptions
import datetime
import random
import sys
import traceback

from vimma.audit import Auditor
from vimma.models import (
    FirewallRule, Expiration, FirewallRuleExpiration,
)
from vimma.util import retry_in_transaction
from vimma.controllers import VMController

from aws.models import AWSVMConfig, AWSVM, AWSFirewallRule, AWSPowerLog
from aws.tasks import power_on_vm, power_off_vm, reboot_vm, destroy_vm, update_vm_status, do_create_vm, route53_add

aud = Auditor(__name__)

class AWSVMController(VMController):
    def power_on(self, user_id=None):
        power_on_vm.delay(self.vm.pk, user_id=user_id)

    def power_off(self, user_id=None):
        power_off_vm.delay(self.vm.pk, user_id=user_id)

    def reboot(self, user_id=None):
        reboot_vm.delay(self.vm.pk, user_id=user_id)

    def destroy(self, user_id=None):
        destroy_vm.delay(self.vm.pk, user_id=user_id)

    def update_status(self):
        update_vm_status.delay(self.vm.pk)

    def create_firewall_rule(self, data, user_id=None):
        create_firewall_rule(self.vm.pk, data,
                user_id=user_id)

    def delete_firewall_rule(self, fw_rule_id, user_id=None):
        delete_firewall_rule(fw_rule_id, user_id=user_id)

    def power_log(self, powered_on):
        AWSPowerLog.objects.create(vm=self.vm, powered_on=powered_on)

    def create_vm_details(self, name, comment, project, schedule, config, user, expiration, sched_override_tstamp):
        aws_vm = AWSVM.objects.create(
                name=name,
                comment=comment,

                project=project,
                schedule=schedule,
                config=config,
                created_by=user,
                expiration=expiration,

                sched_override_state=True,
                sched_override_tstamp=sched_override_tstamp,
                )

        callables = [lambda: do_create_vm.delay(config.id,
            aws_vm_config.root_device_size, config.root_device_volume_type,
            vm.id, user_id)]
        return aws_vm, callables

def ec2_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto EC2Connection to the given AWS VM's region.
    """
    vm = AWSVM.objects.get(id=aws_vm_id)
    return boto.ec2.connect_to_region(vm.region,
            aws_access_key_id=os.getenv(vm.config.provider.access_key_id),
            aws_secret_access_key=os.getenv(vm.config.provider.access_key_secret),)


def route53_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto Route53Connection to the given AWS VM's region.
    """
    vm = AWSVM.objects.get(id=aws_vm_id)
    return boto.route53.connect_to_region(vm.region,
            aws_access_key_id=os.getenv(vm.config.provider.access_key_id),
            aws_secret_access_key=os.getenv(vm.config.provider.access_key_secret),)


def vpc_connect_to_aws_vm_region(aws_vm_id):
    """
    Return a boto VPCConnection to the given AWS VM's region.
    """
    vm = AWSVM.objects.get(id=aws_vm_id)
    return boto.vpc.connect_to_region(vm.region,
            aws_access_key_id=os.getenv(vm.config.provider.access_key_id),
            aws_secret_access_key=os.getenv(vm.config.provider.access_key_secret),)





def do_create_vm_impl(aws_vm_config_id, root_device_size,
        root_device_volume_type, vm_id, user_id):
    """
    The implementation for the similarly named task.

    This function provides the functionality, the task does exception handling.
    """
    # Make the API calls only once. Retrying failed DB transactions must only
    # include idempotent code, not the AWS API calls which create more VMs.

    vm = AWSVM.objects.get(id=vm_id)

    ssh_key_name = vm.config.provider.ssh_key_name
    default_security_group_id = vm.config.provider.default_security_group_id
    vpc_id = vm.config.provider.vpc_id
    name = vm.name
    ami_id = vm.config.ami_id
    instance_type = vm.config.instance_type

    user_data = vm.config.provider.user_data.format(vm=vm).encode('utf-8')

    ec2_conn = ec2_connect_to_aws_vm_region(vm.pk)

    security_group = ec2_conn.create_security_group(
            '{}-{}'.format(name, vm_id), 'Vimma-generated', vpc_id=vpc_id)
    sec_grp_id = security_group.id

    AWSVM.objects.filter(id=vm_id).update(security_group_id=sec_grp_id)

    security_group_ids = [sec_grp_id]
    if default_security_group_id:
        security_group_ids.append(default_security_group_id)

    vpc_conn = vpc_connect_to_aws_vm_region(aws_vm_id)
    subnets = vpc_conn.get_all_subnets(filters={'vpcId': [vpc_id]})
    subnet_id = random.choice(subnets).id

    img = ec2_conn.get_image(ami_id)
    bdm = img.block_device_mapping
    # Passing the image's BDM to run_instances raises:
    # ‘Parameter encrypted is invalid. You cannot specify the encrypted flag if
    # specifying a snapshot id in a block device mapping’.
    # Un-set the offending flag(s): encrypted.
    bdm[img.root_device_name].size = root_device_size
    bdm[img.root_device_name].volume_type = root_device_volume_type
    for k in bdm:
        bdm[k].encrypted = None

    reservation = ec2_conn.run_instances(ami_id,
            instance_type=instance_type,
            security_group_ids=security_group_ids,
            subnet_id=subnet_id,
            block_device_map=bdm,
            key_name=ssh_key_name or None,
            user_data=user_data or None)

    aud.info('Got AWS reservation', user_id=user_id, vm_id=vm_id)

    inst = None
    inst_id = ''
    if len(reservation.instances) != 1:
        aud.error('AWS reservation has {} instances, expected 1'.format(
            len(reservation.instances)), user_id=user_id, vm_id=vm_id)
    else:
        inst = reservation.instances[0]
        inst_id = inst.id

    # By now, the DB state (e.g. fields we don't care about) may have changed.
    # Don't overwrite the DB with our stale field values (from before the API
    # calls). Instead, read&update the DB.

    AWSVM.objects.filter(id=vm_id).update(reservation_id=reservation.id,
        instance_id=inst_id)

    if inst:
        inst.add_tags({
            'Name': name,
            'VimmaSpawned': str(True),
        })

    route53_add.delay(vm_id, user_id=user_id)



def mark_vm_destroyed_if_needed(vm):
    """
    Mark the parent .vm model destroyed if the awsvm is destroyed, else no-op.

    This function may only be called inside a transaction.
    """
    if vm.instance_terminated and vm.security_group_deleted:
        vm.destroyed_at = datetime.datetime.utcnow().replace(tzinfo=utc)
        vm.save()


def create_firewall_rule(vm_id, data, user_id=None):
    """
    data: {
        ip_protocol: string,
        from_port: int,
        to_port: int,
        cidr_ip: string,
    }
    """
    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        with transaction.atomic():
            vm = AWSVM.objects.get(id=vm_id)
            raise('TODO: FireWallRule(vm=vm) is deprecated')
            base_fw_rule = FirewallRule.objects.create(vm=vm)

            ip_protocol = data['ip_protocol']
            from_port, to_port = data['from_port'], data['to_port']
            cidr_ip = data['cidr_ip']
            aws_fw_rule = AWSFirewallRule.objects.create(
                    firewallrule=base_fw_rule,
                    ip_protocol=ip_protocol,
                    from_port=from_port,
                    to_port=to_port,
                    cidr_ip=cidr_ip)
            aws_fw_rule.full_clean()

            now = datetime.datetime.utcnow().replace(tzinfo=utc)
            expire_dt = now + datetime.timedelta(
                    seconds=settings.NORMAL_FIREWALL_RULE_EXPIRY_SECS
                    if not aws_fw_rule.is_special()
                    else settings.SPECIAL_FIREWALL_RULE_EXPIRY_SECS)
            expiration = Expiration.objects.create(
                    type=Expiration.TYPE_FIREWALL_RULE, expires_at=expire_dt)
            expiration.full_clean()
            FirewallRuleExpiration.objects.create(
                    expiration=expiration,
                    firewallrule=base_fw_rule).full_clean()

            conn = ec2_connect_to_aws_vm_region(vm.id)
            conn.authorize_security_group(group_id=vm.security_group_id,
                    ip_protocol=ip_protocol,
                    from_port=from_port,
                    to_port=to_port,
                    cidr_ip=cidr_ip)

        aud.info('Created a firewall rule', vm_id=vm_id, user_id=user_id)


def delete_firewall_rule(fw_rule_id, user_id=None):
    def get_vm_id():
        fw_rule = FirewallRule.objects.get(id=fw_rule_id)
        return fw_rule.vm.id
    vm_id = retry_in_transaction(get_vm_id)

    with aud.ctx_mgr(vm_id=vm_id, user_id=user_id):
        fw_rule = FirewallRule.objects.get(id=fw_rule_id)
        afr = fw_rule.awsfirewallrule
        awsvm = fw_rule.vm.awsvm
        conn = ec2_connect_to_aws_vm_region(awsvm.id)
        conn.revoke_security_group(group_id=awsvm.security_group_id,
                ip_protocol=afr.ip_protocol,
                from_port=afr.from_port,
                to_port=afr.to_port,
                cidr_ip=afr.cidr_ip)
        fw_rule.delete()

    aud.info('Deleted a firewall rule', vm_id=vm_id, user_id=user_id)

