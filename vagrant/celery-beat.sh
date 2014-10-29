#! /usr/bin/env bash

. /home/vagrant/env/bin/activate
DJANGO_SETTINGS_MODULE=vimmasite.settings
PYTHONPATH=/vagrant/vimmasite
export DJANGO_SETTINGS_MODULE PYTHONPATH
exec celery -A vimma.celery:app beat -l info -f /home/vagrant/beat.log
