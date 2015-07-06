[![Build Status](https://travis-ci.org/futurice/vimma2.svg?branch=master)](https://travis-ci.org/futurice/vimma2)

# Provision and manage virtual machines from cloud providers (AWS)

Vimma is Free Software published under the BSD 3-clause license.
See the file `COPYING`.

```
The deploy/DEPLOY file describes deploying to a production server.
The CONF file describes adding VM Providers and Configurations.
The DOC file has some explanations about the structure & features.
```


# Dev Setup:

```bash
cp config/local_settings.py.example config/local_settings.py
# set the SECRET_KEY to a random string
# choose a DB (SQLite3 or PostgreSQL)

cp config/secrets.py.example config/secrets.py
# set the FUM_API_TOKEN used to retrieve Futurice users

cp config/dev_secrets.py.example config/dev_secrets.py
# set up AWS credentials for dev testing
```


## Running in a Vagrant VM (accept the dummy https certificate in your browser):

```bash
vagrant up
# Add ‘127.0.0.1	dev.futurice.com’ to /etc/hosts
```
https://dev.futurice.com:8081/vimma/?dom=shadow


## Running on your machine:

Create a Python3 virtual enviroment and use it for most commands.

```bash
virtualenv -p python3 env
. env/bin/activate
pip install -r req.txt

npm install
PATH=`pwd`/node_modules/.bin:$PATH ./scripts/bower-reset.py	# bower install

mkdir -p vimmasite/static
PYTHONPATH=config ./vimmasite/manage.py collectstatic --noinput --clear --link

PYTHONPATH=config ./vimmasite/manage.py test vimma --settings=test_settings --noinput
PATH=`pwd`/node_modules/.bin:$PATH wct vimmasite/vimma/static/vimma/components/test/

# reset DB, create all permissions and dummy data
PYTHONPATH=config ./scripts/dev-db-reset.py

rabbitmq-server
PYTHONPATH=config ./scripts/worker.py	# start celery worker
PYTHONPATH=config ./scripts/beat.py	# start celery beat (periodic task scheduler)
REMOTE_USER=u2 PYTHONPATH=config ./vimmasite/manage.py runserver
```

http://localhost:8000/vimma/?dom=shadow
