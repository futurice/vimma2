#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


set +u
. /home/vagrant/venv/bin/activate
set -u

DJANGO_SETTINGS_MODULE=vimmasite.settings \
	PYTHONPATH=/vagrant/vimmasite \
	python3 /vagrant/scripts/dev-data/make-data.py
