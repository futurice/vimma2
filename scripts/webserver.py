#! /usr/bin/env python3

import argparse
import subprocess

import util


def parse_args():
    p = argparse.ArgumentParser(description='Run the webserver')
    return p.parse_args()


if __name__ == '__main__':
    parse_args()

    env=util.os_environ_with_venv()
    env['REMOTE_USER'] = 'u2'
    subprocess.check_call([util.MANAGE_PY, 'runserver'], env=env)
