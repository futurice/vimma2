#! /usr/bin/env python3

import argparse
import os, os.path
import subprocess

import util


def parse_args():
    p = argparse.ArgumentParser(description='''Reset DB and migrations, create
        dummy data''')
    return p.parse_args()


def reset():
    subprocess.check_call([os.path.join(util.UTIL_DIR, 'migrations-reset.py')])
    subprocess.check_call([util.MANAGE_PY, 'migrate'],
            env=util.os_environ_with_venv())


def populate():
    env=util.os_environ_with_venv()
    env['DJANGO_SETTINGS_MODULE'] = util.DJANGO_SETTINGS_MODULE
    env['PYTHONPATH'] = util.VIMMASITE_PYTHONPATH
    subprocess.check_call(['python',
        os.path.join(util.UTIL_DIR, 'dev-data', 'make-data.py')],
        env=env)


if __name__ == '__main__':
    parse_args()
    reset()
    populate()
