#! /usr/bin/env python3

import argparse
import os, os.path
import subprocess

import util


def parse_args():
    p = argparse.ArgumentParser(description='''Get all Futurice users
        and create or update a Vimma user for each''')
    return p.parse_args()

if __name__ == '__main__':
    args = parse_args()

    env = dict(os.environ)
    env['DJANGO_SETTINGS_MODULE'] = util.DJANGO_SETTINGS_MODULE
    env['PYTHONPATH'] = util.VIMMASITE_PYTHONPATH
    if 'PYTHONPATH' in os.environ:
        env['PYTHONPATH'] = os.pathsep.join((env['PYTHONPATH'],
                os.environ['PYTHONPATH']))

    subprocess.check_call(['python3',
        os.path.join(util.UTIL_DIR, 'import-futurice-users-impl.py')],
        env=env)
