#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


ROOT_DIR=/vagrant/vagrant

"$ROOT_DIR"/virtualenv.sh
"$ROOT_DIR"/test.sh
"$ROOT_DIR"/collectstatic.sh
"$ROOT_DIR"/migrate.sh

sudo start supervisor
sudo service apache2 start
