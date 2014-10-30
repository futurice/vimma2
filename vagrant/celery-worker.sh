#! /usr/bin/env bash

. /home/vagrant/env/bin/activate
DJANGO_SETTINGS_MODULE=vimmasite.settings
PYTHONPATH=/vagrant/vimmasite:/vagrant/config
export DJANGO_SETTINGS_MODULE PYTHONPATH
exec celery -A vimma.celery:app worker -l info -f /home/vagrant/worker.log
