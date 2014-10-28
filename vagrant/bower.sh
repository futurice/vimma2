#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


# bower complains (on usage) '/usr/bin/env: node: No such file or directory'
ln -s /usr/bin/nodejs /usr/bin/node
npm install -g bower
