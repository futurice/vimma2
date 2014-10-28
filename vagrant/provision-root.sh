#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


# Can't use "$0" because ‘vagrant up’ copies this script to /tmp/vagrant-shell
# and runs that.
ROOT_DIR=/vagrant/vagrant

"$ROOT_DIR"/apt-get.sh
"$ROOT_DIR"/apache-config.sh
"$ROOT_DIR"/supervisor.sh
"$ROOT_DIR"/postgresql.sh
"$ROOT_DIR"/bower.sh
