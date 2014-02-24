import AWS_conn

from VMM_util import *

def create_instance(instance_name=None):
    aws_conn = AWS_conn.EC2Conn()
    aws_conn.connect()
    return aws_conn.create_instance(instance_name=instance_name)

def main(instance_name=None):
    instance = create_instance(instance_name=instance_name)
    print "Instance details: "
    pp.pprint( instance.__dict__ )
    print "Instance listening at: %s" % (instance.ip_address)
    return instance.__dict__
    
if __name__ == "__main__":
    main()
