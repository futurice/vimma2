
VMM2 - Vimma 2 virtual machine management
=========================================

Vimma2 is a prototype of a portal to be used for spawning development virtual machines from AWS.

Overview
--------

The main portal consists of:

- django
- celeryd
- rabbitmq
- nginx
- uwsgi
- postgresql

Additionally:

- Puppet certificate signing integration

It will run inside as an EC2 instance in the same account.

Some URLs of interest
---------------------

- /vmcreatedtime/ - is a public view (no login required) that can be
  polled to check the creation time of a vm in optional format=epoch|iso
  returns "0" on failure or non-existent VM. should be polled by the puppetmaster
  cert signing script.
  eg. http://localhost:8000/vmcreatedtime/demovm139446105600?format=epoch

Todos and action points
-----------------------

- Setting up the environment
 - Pretty much done
- Scheduling
 - WIP
- Puppet master certificate signer
 - WIP
- Billing / Cost visibility
 - WIP - set up on S3 bucket (vmm-billing) - create csw parser, use netflix ice
   or other cheaper variant (ice uses proprietary js libs)

Installation
------------

The portal should be testable locally with the following steps:
- Cloning the repo
- A local postgresql DB and rabbitmq
- Installation of requirements, db sync and migration
- python manage.py runserver & python manage.py celeryd

A bit more detailed installation flow for an ubuntu server:

#### Generic system packages

```bash
root@vmm:~# apt-get install git rabbitmq-server python-pip python-psycopg2 libpq-dev python-dev postgresql-client-common language-pack-fi \
postgresql-client-9.1
# For production add: nginx uwsgi
```

#### PIP packages

- First install virtualenv

```bash
root@vmm:~# sudo pip install virtualenv
root@vmm:~# pip install virtualenvwrapper
```

- Concatenate these lines to .bashrc

```bash
export WORKON_HOME
source /usr/local/bin/virtualenvwrapper.sh
```
- Re-source your profile and actiavate the venv

```bash
% . ~/virtualenvs/vmm/bin/activate
```

- Install requirements

```bash
(vmmtest)vmm@vmm:~/vmm_test/futurice_vimma2$ pip install -r requirements.txt
Downloading/unpacking BeautifulSoup==3.2.1 (from -r requirements.txt (line 1))
  Downloading BeautifulSoup-3.2.1.tar.gz
Successfully installed BeautifulSoup Django Mako MarkupSafe PyYAML South UgliPyJS amqp anyjson assetgen backports.ssl-match-hostname billiard boto celery django-celery kombu psycopg2 pytz requests simp
Cleaning up...
```

- Set up your postgresql locally or via RDS as applicable, check the connection

```bash
root@vmm:~# psql -U vmmtestuser -d vmmtest -h vmm-testdb.dev.futurice.com
Password for user vmmtestuser:
psql (9.1.12, server 9.3.2)
WARNING: psql version 9.1, server version 9.3.
         Some psql features might not work.
SSL connection (cipher: DHE-RSA-AES256-SHA, bits: 256)
Type "help" for help.

vmmtest=>
```
- Configure the local_settings.py

```python
# DB connections
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'vmmtest',
        'USER': 'vmmtestuser',
        'PASSWORD': 'password',
        'HOST': 'vmm-testdb.dev.futurice.com',
        'PORT': '',
    }
}

# AWS connections
AWS_ACCESS_KEY_ID="AKI access key"
AWS_ACCESS_KEY_SECRET="aws secret"
ROUTE53_HOSTED_ZONE_ID="hosted zone id"
```

- Starting up the service for the first time, load venv set up db

```bash
# Load venv
vmm@vmm:~/vmm_test/futurice_vimma2$ . ~/.virtualenvs/vmmtest/bin/activate
# Sync django
(vmmtest)vmm@vmm:~/vmm_test/futurice_vimma2$ python manage.py syncdb
# Migrate db changes
(vmmtest)vmm@vmm:~/vmm_test/futurice_vimma2$ python manage.py migrate

# Insert an initial schedule (optionally through django admin view):

vmmtest=> INSERT INTO vmm_schedule VALUES (1, 'Eight-to-Eight', '08:00:00', '20:00:00', 'tttttff');
INSERT 0 1
```

- Upstart script examples available under https://code.futurice.com/futurice_vimma2/tree/master/extras
