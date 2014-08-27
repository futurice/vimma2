"""
Django settings for vimmasite project.

For more information on this file, see
https://docs.djangoproject.com/en/dev/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/dev/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/dev/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

TEMPLATE_DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'vimma',
    'rest_framework',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.contrib.auth.middleware.RemoteUserMiddleware',
)

AUTHENTICATION_BACKENDS = (
    'vimma.backends.RemoteNoUnknownUserBackend',
)

ROOT_URLCONF = 'vimmasite.urls'

WSGI_APPLICATION = 'vimmasite.wsgi.application'


# Internationalization
# https://docs.djangoproject.com/en/dev/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/dev/howto/static-files/

STATIC_URL = '/static/'


REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    # TODO: find an appropiate global page size, maybe override it for some
    # views, or even allow the client to choose with ?queryParam=value&
    # http://www.django-rest-framework.org/api-guide/pagination#pagination-in-the-generic-views
    'PAGINATE_BY': 10,
}


# Logging Configuration

import logging
import time

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
        'fileH': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'fmt',
            'filename': 'vimma.log',
            'encoding': 'utf-8',
            'maxBytes': 2*1024*1024,
            'backupCount': 5,
        },
    },
    'root': {
        'level': 'NOTSET',
        'handlers': ['consoleH', 'fileH'],
    },
}


from local_settings import *
