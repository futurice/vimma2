import os
from celery import Celery


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'vimmasite.settings')
app = Celery(include=['vimma.vmutil', 'vimma.vmtype.dummy'])
app.config_from_object('vimma.celeryconfig')
