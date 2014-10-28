#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


ROOT_DIR=/vagrant/vagrant

"$ROOT_DIR"/virtualenv.sh
"$ROOT_DIR"/../scripts/polymerjs-reset.py
"$ROOT_DIR"/migrate.sh
"$ROOT_DIR"/import-futurice-users.sh
"$ROOT_DIR"/make-dev-data.sh
