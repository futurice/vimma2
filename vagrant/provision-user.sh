#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


ROOT_DIR=/vagrant/vagrant

"$ROOT_DIR"/virtualenv.sh

# this is time-consuming, only get Polymer if it's not already present
if [ ! -e /vagrant/vimmasite/vimma/static/vimma/components/bower_components ]; then
	"$ROOT_DIR"/../scripts/polymerjs-reset.py
fi

"$ROOT_DIR"/dev-db-reset.sh
