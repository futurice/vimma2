import sys
import time

import boto
from boto.ec2.connection import EC2Connection

from VMM_util import *
from settings import *
from local_settings import *


SERVER_TYPES = {
                'vmm01' : {
                       'image_id' : DEFAULT_AMI_ID,
                       'instance_type' : 't1.micro',
                       'security_groups' : [DEFAULT_SECURITYGROUP],
                       'key_name' : DEFAULT_KEYPAIR_NAME,
                       'instance_initiated_shutdown_behavior' : 'stop',
                        },
}


class EC2Conn:
        def __init__(self):
                self.conn = None
                self.access_key = AWS_ACCESS_KEY_ID
                self.secret_key = AWS_ACCESS_KEY_SECRET
                self.region = boto.ec2.get_region(DEFAULT_REGION)

        def connect(self):
                self.conn = EC2Connection(aws_access_key_id=self.access_key, aws_secret_access_key=self.secret_key, region=self.region)
                print "Connection: %s" % self.conn

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
                
                # Set delete on termination
                instance.modify_attribute('blockDeviceMapping', { '/dev/sda1' : True })

                # Set instance name
                self.conn.create_tags([instance.id], {"Name": instance_name})

                if address:
                        success = self.link_instance_and_ip(instance.id, address)
                        if success:
                                print "Linked %s to %s" % (instance.id, address)
                        else:
                                print "Failed to link %s to %s" % (instance.id, address)
                        instance.update()

                return instance

        def terminate_instance(self, instance_id):
            self.conn.terminate_instances(instance_ids=[instance_id])
            """
            try:
                self.conn.terminate_instance(instance_id)
            except:
                return False;
            return True;
            """

        def stop_instance(self, instance_id):
            try:
                self.conn.stop_instance(instance_id)
            except:
                return False;
            return True;


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
