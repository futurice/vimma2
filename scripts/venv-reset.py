#! /usr/bin/env python3

import argparse
import os, os.path
import shutil
import subprocess

import util


def parse_args():
    p = argparse.ArgumentParser(description='''Delete then setup Python3
        virtual environment in {}'''.format(util.VENV_DIR))
    return p.parse_args()


def delete_venv():
    if os.path.lexists(util.VENV_DIR):
        shutil.rmtree(util.VENV_DIR)


def make_venv():
    subprocess.check_call(['virtualenv', '-p', 'python3', util.VENV_DIR])


def pip_install():
    subprocess.check_call(['pip', 'install', '-r', util.REQ_FILE],
            env=util.os_environ_with_venv())


if __name__ == '__main__':
    args = parse_args()
    delete_venv()
    make_venv()
    pip_install()
