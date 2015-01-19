#! /usr/bin/env bash

set -u  # exit if using uninitialised variable
set -e  # exit if some command in this script fails
trap "echo $0 failed because a command in the script failed" ERR


# Install apt-get packages

sed -e 's/archive.ubuntu.com/de.archive.ubuntu.com/g' -i /etc/apt/sources.list

apt-get update
apt-get install -y \
	build-essential vim htop \
	apache2 libapache2-mod-auth-pubtkt libapache2-mod-wsgi-py3 \
	rabbitmq-server python3 python3-pip python-virtualenv \
	supervisor postgresql libpq-dev python-dev \
	npm git \
	xvfb chromium-browser chromium-chromedriver firefox
# Use python3-virtualenv instead, in distributions that have it
