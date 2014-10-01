#! /usr/bin/env python3

import argparse
import os, os.path
import shutil
import subprocess

import util


MIGRATIONS_DIR = os.path.join(util.PRJ_ROOT, 'vimmasite/vimma/migrations')


def parse_args():
    p = argparse.ArgumentParser(description='''Delete DB & migrations then
        make migrations in {}'''.format(MIGRATIONS_DIR))
    return p.parse_args()


if __name__ == '__main__':
    args = parse_args()

    if os.path.lexists(util.DB_FILE):
        os.remove(util.DB_FILE)
    if os.path.lexists(MIGRATIONS_DIR):
        shutil.rmtree(MIGRATIONS_DIR)

    os.mkdir(MIGRATIONS_DIR)
    with open(os.path.join(MIGRATIONS_DIR, '__init__.py'), 'x'):
        pass
    subprocess.check_call([util.MANAGE_PY, 'makemigrations'],
            env=util.os_environ_with_venv())
