#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


# All dependencies are met (virtual environmet, db migrations, etc).
# Start the supervisor daemon.
start supervisor
