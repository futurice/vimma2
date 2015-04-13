#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


set +u
. /home/vagrant/env/bin/activate
set -u
# --noinput destroys old test DB if it exists (else prompts the user and fails)
# Ubuntu 14.04's chromium-chromedriver needs the PATH and LD_LIBRARY_PATH
PATH=$PATH:/usr/lib/chromium-browser \
	LD_LIBRARY_PATH=/usr/lib/chromium-browser/libs \
	PYTHONPATH=/vagrant/config \
	xvfb-run /vagrant/vimmasite/manage.py test vimma --settings=test_settings --noinput

cd /vagrant
PATH=$PATH:/usr/local/lib/node_modules/vimma2/node_modules/.bin \
	xvfb-run wct vimmasite/vimma/static/vimma/components/test/
