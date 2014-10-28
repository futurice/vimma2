#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


# Create (or reuse the existing) python virtual environment, then pip install
VENV=/home/vagrant/venv
if [ ! -e "$VENV" ]; then
	virtualenv -p python3 "$VENV"
fi

set +u
. "$VENV"/bin/activate
set -u
pip install -r /vagrant/req.txt
