#! /usr/bin/env python3

# https://docs.djangoproject.com/en/1.7/releases/1.7/#standalone-scripts
import django
django.setup()

import argparse
from django.conf import settings
import os, os.path
import subprocess
import sys

import util


def parse_args():
    p = argparse.ArgumentParser(description='''The implementation for
        delete-db.py, called by that script.''')
    return p.parse_args()


def delete_db():
    n = settings.DATABASES['default']['ENGINE']
    if n == 'django.db.backends.sqlite3':
        if os.path.lexists(util.DB_FILE):
            os.remove(util.DB_FILE)
    elif n == 'django.db.backends.postgresql_psycopg2':
        dbname = settings.DATABASES['default']['NAME']
        subprocess.call(['dropdb', dbname])
        subprocess.check_call(['createdb', dbname])
    else:
        print('Unknown DB engine', n, file=sys.stderr)


if __name__ == '__main__':
    args = parse_args()
    delete_db()
