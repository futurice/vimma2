#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR

SCRIPT=`readlink -f "$0"`
SCRIPT_DIR=`dirname "$SCRIPT"`


# Move Supervisor from the init system to upstart
service supervisor stop
update-rc.d supervisor disable

cp "$SCRIPT_DIR"/supervisor.conf /etc/init/supervisor.conf
cp "$SCRIPT_DIR"/supervisor-conf.d/* /etc/supervisor/conf.d/
