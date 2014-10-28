#! /usr/bin/env bash

. /home/vagrant/venv/bin/activate
DJANGO_SETTINGS_MODULE=vimmasite.settings
PYTHONPATH=/vagrant/vimmasite
export DJANGO_SETTINGS_MODULE PYTHONPATH
exec celery -A vimma.celery:app worker -l info -f /home/vagrant/worker.log
