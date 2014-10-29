#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


echo 'nameserver 8.8.8.8
nameserver 208.67.220.220' > /etc/resolv.conf
