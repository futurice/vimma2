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
