import inspect
import os, os.path
import sys


_MOD_PATH = os.path.realpath(inspect.getfile(sys.modules[__name__]))
UTIL_DIR = os.path.dirname(_MOD_PATH)


PRJ_ROOT = os.path.dirname(UTIL_DIR)

MANAGE_PY = os.path.join(PRJ_ROOT, 'vimmasite', 'manage.py')
DB_FILE = os.path.join(PRJ_ROOT, 'vimmasite', 'db.sqlite3')

DJANGO_SETTINGS_MODULE = 'vimmasite.settings'
# Entry to add to PYTHONPATH when not running via manage.py
VIMMASITE_PYTHONPATH = os.path.join(PRJ_ROOT, 'vimmasite')
