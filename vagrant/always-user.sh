#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


ROOT_DIR=/vagrant/vagrant

"$ROOT_DIR"/virtualenv.sh

# only do ‘bower install’ if missing
if [ ! -e /vagrant/vimmasite/vimma/static/vimma/components/bower_components ]; then
	"$ROOT_DIR"/../scripts/bower-reset.py
fi

"$ROOT_DIR"/test.sh
"$ROOT_DIR"/collectstatic.sh
"$ROOT_DIR"/migrate.sh

sudo service supervisor start
sudo service apache2 start
