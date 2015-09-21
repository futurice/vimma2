[![Build Status](https://travis-ci.org/futurice/vimma2.svg?branch=master)](https://travis-ci.org/futurice/vimma2)

# Provision and manage virtual machines from cloud providers ()

Vimma is Free Software published under the BSD 3-clause license.
See the file `COPYING`.

```
The CONF file describes adding VM Providers and Configurations.
The DOC file has some explanations about the structure & features.
```

## Running with Docker:

```bash
docker build --rm --tag futurice/vimmadev -f docker/dev/Dockerfile .
docker run --name postgres -e POSTGRES_PASSWORD=mysecretpassword -d postgres
docker run --rm -it -p 8000:8000 --name vimma \
    -e DB_USER=postgres \
    -e DB_HOST=postgres \
    -e DB_PASSWORD=mysecretpassword \
    -e DEBUG=true \
    -e CELERY_LOG_LEVEL=debug \
    -e AWS_ACCESS_KEY_ID="" \
    -e AWS_ACCESS_KEY_SECRET="" \
    -e AWS_SSH_KEY_NAME="" \
    -e AWS_ROUTE_53_NAME="" \
    -e AWS_DEFAULT_SECURITY_GROUP_ID="" \
    -e AWS_VPC_ID="" \
    -v ~/vimma/:/opt/app/:rw \
    --link postgres:postgres \
    futurice/vimmadev
```
http://DOCKER_IP:8000/?dom=shadow
http://DOCKER_IP:8000/admin/

```bash
# create a database
docker exec -it postgres bash
su postgres; createdb vimma;

# add an admin user
docker exec -it vimma python3 manage.py createsuperuser --username vimma --email vimma@company.com

# run tests
docker exec -it vimma xvfb-run python3 manage.py test --noinput
docker exec -it vimma xvfb-run ../static/node_modules/.bin/wct ui/components/test/
```

## Adding support for further cloud providers:

A Provider has Config(s), that are used to create VM(s).
The vimma.models provide an interface for building VM implementations.

### Implementing a new VM:

1) my.controller:
```python
class VMController(vimma.controllers.VMController):
    pass
```

2) my.models:
```python
class VM(vimma.models.VM):
    controller_cls = ('my.controller', 'VMController')
    config = models.ForeignKey('my.Config', on_delete=models.PROTECT, related_name="vm")

class Provider(vimma.models.Provider):
    pass

class Config(vimma.models.Config):
    provider = models.ForeignKey('my.Provider', on_delete=models.PROTECT, related_name="config")

class FirewallRule(vimma.models.FirewallRule):
    vm = models.ForeignKey('my.VM', related_name="firewallrule")

class FirewallRuleExpiration(vimma.models.FirewallRuleExpiration):
    firewallrule = models.OneToOneField('my.FirewallRule', related_name="expiration")

class Expiration(vimma.models.Expiration):
    vm = models.OneToOneField('my.VM', related_name="expiration")

class PowerLog(vimma.models.PowerLog):
    vm = models.ForeignKey('my.VM', related_name="powerlog")
```

