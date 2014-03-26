"""
 Portions copyright: Jeff Hull, http://engineerwithoutacause.com/amazon-ec2-deployment-with-boto.html
 Used with permission :"Feel free to use as you want. Would appreciate a name reference in case
 someone wants to find original source!"
"""

import sys
import time

import boto

from boto.ec2.connection import EC2Connection

from boto.route53.connection import Route53Connection
from boto.route53.record import ResourceRecordSets

from VMM_util import *
from settings import *
from vimma2.local_settings import *


SERVER_TYPES = {
    'vmm01' : {
        'image_id' : DEFAULT_AMI_ID,
        'instance_type' : 't1.micro',
        'security_groups' : [DEFAULT_SECURITYGROUP],
        'key_name' : DEFAULT_KEYPAIR_NAME,
        'instance_initiated_shutdown_behavior' : 'stop',
              },
}

class Route53Conn:
    def __init__(self):
        self.conn = None
        self.access_key = AWS_ACCESS_KEY_ID
        self.secret_key = AWS_ACCESS_KEY_SECRET
        self.hosted_zone_id = ROUTE53_HOSTED_ZONE_ID

    def connect(self):
        self.conn = Route53Connection(aws_access_key_id=self.access_key, aws_secret_access_key=self.secret_key)
        print "Connection: %s" % self.conn

    def alter_cname(self, vm_name, public_dns_name, action):
        changes = ResourceRecordSets(self.conn, self.hosted_zone_id)
        change = changes.add_change(action, vm_name + DOMAIN_SUFFIX, "CNAME")
        change.add_value(public_dns_name)
        result = changes.commit()
        return result

    def create_cname(self, vm_name, public_dns_name):
        return self.alter_cname(vm_name, public_dns_name, "CREATE")

    def remove_cname(self, vm_name, public_dns_name):
        return self.alter_cname(vm_name, public_dns_name, "DELETE")



class EC2Conn:
    def __init__(self):
        self.conn = None
        self.access_key = AWS_ACCESS_KEY_ID
        self.secret_key = AWS_ACCESS_KEY_SECRET
        self.region = boto.ec2.get_region(DEFAULT_REGION)

    def connect(self):
        self.conn = EC2Connection(aws_access_key_id=self.access_key, aws_secret_access_key=self.secret_key, region=self.region)
        print "Connection: %s" % self.conn

    def describe_instance(self, instance_id):
        #reservations = self.conn.get_all_instances(instance_ids=[instance_id])
        #instance = reservations[0].instances[0]
        instances = self.conn.get_only_instances(instance_ids=[instance_id])
        instance = instances[0]
        return instance

    def describe_all_instances(self):
        instances = self.conn.get_only_instances()
        return instances


    def create_instance(self, instance_type='vmm01', instance_name=None, address=None):
        reservation = self.conn.run_instances( **SERVER_TYPES[instance_type])
        print reservation
        instance = reservation.instances[0]
        time.sleep(10)

        while instance.state != 'running':
            time.sleep(5)
            instance.update()
            print "Instance state: %s" % (instance.state)

        print "Instance details: %s" % (instance)
        print "Instance %s done!" % (instance.id)

        # Set delete on termination to True
        instance.modify_attribute('blockDeviceMapping', { '/dev/sda1' : True })

        # Set instance name and other tags
        self.conn.create_tags([instance.id], {"Name": instance_name})
        self.conn.create_tags([instance.id], {"VimmaSpawned": True})
        return instance

    def terminate_instance(self, instance_id):
        self.conn.terminate_instances(instance_ids=[instance_id])

    def poweroff_instance(self, instance_id):
        self.conn.stop_instances(instance_ids=[instance_id])

    def poweron_instance(self, instance_id):
        print "Poweron instance %s" % instance_id
        instance = self.describe_instance(instance_id)
        instance.start()

        while instance.state != 'running':
            time.sleep(5)
            instance.update()
            print "Instance state: %s" % (instance.state)
        return instance

    def link_instance_and_ip(self, instance_id, ip=None):
        success = self.conn.associate_address(instance_id=instance_id, public_ip=ip)

        if success:
            print "Sleeping for 60 seconds to let IP attach"
            time.sleep(60)

        return success

    def unlink_instance_and_ip(self, instance_id, ip=None):
        return self.conn.disassociate_address(instance_id=instance_id, public_ip=ip)

    def get_instances(self):
            return self.conn.get_all_instances()
