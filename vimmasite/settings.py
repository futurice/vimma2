import django.conf.global_settings as DEFAULT_SETTINGS
from ast import literal_eval
import os
import logging
import time

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')
SECRET_KEY = os.getenv('SECRET_KEY', '')

ADMINS = (
    'jussi.vaihia@futurice.com',
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.getenv('DB_NAME', 'vimma'),
        'USER': os.getenv('DB_USER', 'vimma'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'vimma'),
        'HOST': os.getenv('DB_HOST', 'postgres'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [],
    'APP_DIRS': True,
    'OPTIONS': {
        'context_processors': [
            'django.contrib.auth.context_processors.auth',
            'django.template.context_processors.i18n',
            'django.template.context_processors.media',
            'django.template.context_processors.static',
            'django.template.context_processors.tz',],
        'debug': DEBUG,}
}]

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'vimma',
    'dummy',
    'aws',

    'rest_framework',
    'django_extensions',
    'django_js_utils',
)

STATICFILES_DIRS = list(DEFAULT_SETTINGS.STATICFILES_DIRS)
STATICFILES_DIRS += [
    os.path.join(BASE_DIR, '..', 'static/'),
    os.path.join(BASE_DIR, 'ui'),
    '/usr/local/lib/python3.4/dist-packages/django/contrib/admin/static/',
    '/usr/local/lib/python3.4/dist-packages/rest_framework/static/',
    '/usr/local/lib/python3.4/dist-packages/django_extensions/static/',
    '/usr/local/lib/python3.4/dist-packages/django_js_utils/static/',
    ]

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'vimma.auth.CustomHeaderMiddleware',# a configurable 'django.contrib.auth.middleware.RemoteUserMiddleware'
)

AUTHENTICATION_BACKENDS = literal_eval(os.getenv('AUTHENTICATION_BACKENDS')) \
        if os.getenv('AUTHENTICATION_BACKENDS') else DEFAULT_SETTINGS.AUTHENTICATION_BACKENDS
REMOTE_USER_ENABLED = os.getenv('REMOTE_USER_ENABLED', 'false').lower() == 'true'

ROOT_URLCONF = 'vimmasite.urls'

WSGI_APPLICATION = 'vimmasite.wsgi.application'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
LIVE_SERVER_URL = 'http://localhost:8000'# TOOD: see test_live.py

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # http://www.django-rest-framework.org/api-guide/pagination/#pagenumberpagination
    'DEFAULT_PAGINATION_CLASS': 'vimmasite.pagination.VimmaPagination',
    'PAGE_SIZE': 100,
}

# Log UTC times
logging.Formatter.converter = time.gmtime
LOGGING = {
    'version': 1,
    'formatters': {
        'fmt': {
            'format': '%(asctime)s %(levelname)s:%(name)s:%(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S %z (%Z)',
        },
    },
    'handlers': {
        'consoleH': {
            'class': 'logging.StreamHandler',
            'level': 'WARNING',
            'formatter': 'fmt',
        },
    },
    'root': {
        'level': 'NOTSET',
        'handlers': ['consoleH'],
    },
}

AUTH_USER_MODEL = 'vimma.User'

# On VM creation, set a schedule override to keep it Powered On.
VM_CREATION_OVERRIDE_SECS = 60*60
secs_in_day = 60*60*24

# Default VM expiration - 3 months
# This is also the maximum amount of time in the future that one can extend the expiration to.
DEFAULT_VM_EXPIRY_SECS = secs_in_day*30*3

# Notification intervals relative to expiration date
VM_NOTIFICATION_INTERVALS = [x*secs_in_day for x in
        [-14, -7, -3, -2, -1, 0, 1, 2]]

# Keep VM for this amount of time after expiration
VM_GRACE_INTERVAL = secs_in_day*14

# Firewall rule expiration
NORMAL_FIREWALL_RULE_EXPIRY_SECS = secs_in_day * 30 * 3
SPECIAL_FIREWALL_RULE_EXPIRY_SECS = secs_in_day * 7

TRUSTED_NETWORKS = ['10.0.0.0/8', '192.168.0.0/16', '172.16.0.0/12']

EC2_DEFAULT_REGION = 'us-east-1'

# django_js_utils
URLS_EXCLUDE_PREFIX = ['^admin',]
URLS_EXCLUDE_PATTERN = ['.(?P<format>[a-z0-9]+)','.(?P<format>+)','__debug__',]

del secs_in_day

try:
    from local_settings import *
except Exception as e:
    pass
