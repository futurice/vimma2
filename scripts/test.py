#! /usr/bin/env python3

import argparse
import os, os.path
import subprocess

import util


def parse_args():
    p = argparse.ArgumentParser(description='Reset migrations then run tests')
    return p.parse_args()


if __name__ == '__main__':
    parse_args()
    subprocess.check_call([os.path.join(util.UTIL_DIR, 'migrations-reset.py')])
    subprocess.check_call(
            [util.MANAGE_PY, 'test', 'vimma', '--settings=test_settings'],
            env=util.os_environ_with_venv())
