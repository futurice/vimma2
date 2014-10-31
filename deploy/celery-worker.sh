#! /usr/bin/env bash

. /home/vimma2/env/bin/activate
DJANGO_SETTINGS_MODULE=vimmasite.settings
PYTHONPATH=/home/vimma2/vimma2/vimmasite:/home/vimma2/config
export DJANGO_SETTINGS_MODULE PYTHONPATH
exec celery -A vimma.celery:app worker -l info -f /home/vimma2/worker.log
