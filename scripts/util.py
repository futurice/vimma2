import inspect
import os, os.path
import sys


_MOD_PATH = os.path.realpath(inspect.getfile(sys.modules[__name__]))
UTIL_DIR = os.path.dirname(_MOD_PATH)


PRJ_ROOT = os.path.dirname(UTIL_DIR)
VENV_DIR = os.path.join(PRJ_ROOT, 'env')
REQ_FILE = os.path.join(PRJ_ROOT, 'req.txt')

MANAGE_PY = os.path.join(PRJ_ROOT, 'vimmasite', 'manage.py')
DB_FILE = os.path.join(PRJ_ROOT, 'vimmasite', 'db.sqlite3')

DJANGO_SETTINGS_MODULE = 'vimmasite.settings'
# Entry to add to PYTHONPATH when not running via manage.py
VIMMASITE_PYTHONPATH = os.path.join(PRJ_ROOT, 'vimmasite')


def os_environ_with_venv():
    """
    Return a copy of the os.environ mapping with venv's bin/ prepended to PATH.

    Use this as the env argument to subprocess.call & friends.
    """
    env = dict(os.environ)
    env['PATH'] = os.path.join(VENV_DIR, 'bin') + os.pathsep + env['PATH']
    return env
