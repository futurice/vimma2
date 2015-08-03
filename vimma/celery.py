from celery import Celery


app = Celery(include=['vimma.vmutil', 'vimma.vmtype.dummy'])
app.config_from_object('vimma.celeryconfig')
