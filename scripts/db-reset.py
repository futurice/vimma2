#! /usr/bin/env python3

import argparse
import os, os.path
import subprocess

import util


env = dict(os.environ)
env.update({
    'DJANGO_SETTINGS_MODULE': util.DJANGO_SETTINGS_MODULE,
    'PYTHONPATH': util.VIMMASITE_PYTHONPATH,
})


def parse_args():
    p = argparse.ArgumentParser(description='''Reset DB, create dummy data''')
    return p.parse_args()


def populate():
    subprocess.check_call([
        os.path.join(util.UTIL_DIR, 'import-futurice-users.py')])
    subprocess.check_call(['python',
        os.path.join(util.UTIL_DIR, 'make-dev-data.py')], env=env)


if __name__ == '__main__':
    parse_args()
    subprocess.check_call([os.path.join(util.UTIL_DIR, 'delete-db.py')])
    subprocess.check_call([util.MANAGE_PY, 'migrate'])
    populate()
