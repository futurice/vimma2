#! /usr/bin/env python3

import argparse
import os, os.path
import subprocess

import util


def parse_args():
    p = argparse.ArgumentParser(description='''Delete the DB (and recreate it
            if it's PostgreSQL)''')
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()

    env = dict(os.environ)
    env.update({
        'DJANGO_SETTINGS_MODULE': util.DJANGO_SETTINGS_MODULE,
        'PYTHONPATH': util.VIMMASITE_PYTHONPATH,
    })
    subprocess.check_call(['python3',
        os.path.join(util.UTIL_DIR, 'delete-db-impl.py')], env=env)
