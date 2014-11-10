#! /usr/bin/env python3

import argparse
import os, os.path
import shutil
import subprocess

import util


COMP_DIR = os.path.join(util.PRJ_ROOT,
        'vimmasite/vimma/static/vimma/components')
BOWER_COMP_DIR = os.path.join(COMP_DIR, 'bower_components')

def parse_args():
    p = argparse.ArgumentParser(description='''Delete then bower install
            in {}'''.format(BOWER_COMP_DIR))
    return p.parse_args()


def delete_bower_comp_dir():
    if os.path.lexists(BOWER_COMP_DIR):
        shutil.rmtree(BOWER_COMP_DIR)


def bower_install():
    subprocess.check_call(['bower', 'install',
        # disable the ‘may bower report statistics?’ question
        '--config.interactive=false'],
        cwd=COMP_DIR)


if __name__ == '__main__':
    args = parse_args()
    delete_bower_comp_dir()
    bower_install()
