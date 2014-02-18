import AWS_conn

from VMM_util import *

def create_instance():
    aws_conn = AWS_conn.EC2Conn()
    aws_conn.connect()
    return aws_conn.create_instance()

def main():
    instance = create_instance()
    print "Instance details: "
    pp.pprint( instance.__dict__ )
    print "Instance listening at: %s" % (instance.ip_address)
    
if __name__ == "__main__":
    main()
