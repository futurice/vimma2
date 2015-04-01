#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


cd /vagrant
# Like the virtualenv, this needn't be global, but unlike the venv I don't
# think we can have local ‘node_modules’ outside the repo root (current dir)
# and we don't want to interfere with any venv or node_modules the developer
# may be using on his own machine, outside vagrant.
npm install -g
