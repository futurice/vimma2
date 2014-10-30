#! /usr/bin/env python3

import argparse
import os, os.path
import subprocess

import util


def parse_args():
    p = argparse.ArgumentParser(description='''Start Celery worker''')
    return p.parse_args()


if __name__ == '__main__':
    parse_args()

    env = dict(os.environ)
    env['DJANGO_SETTINGS_MODULE'] = util.DJANGO_SETTINGS_MODULE
    env['PYTHONPATH'] = util.VIMMASITE_PYTHONPATH
    if 'PYTHONPATH' in os.environ:
        env['PYTHONPATH'] = os.pathsep.join((env['PYTHONPATH'],
                os.environ['PYTHONPATH']))

    # add ‘-f logfile’ to send the log to a file
    p = subprocess.Popen(['celery', '-A', 'vimma.celery:app', 'worker',
        '-l', 'info'], env=env)
    # Ctrl-C gets sent to both the parent and child processes. Wait for celery
    # to exit. Else celery processes are left after the python script exits.
    while True:
        try:
            p.wait()
            break
        except KeyboardInterrupt:
            pass
