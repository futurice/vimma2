from celery import Celery


app = Celery(include=['vimma.vmutil', 'dummy.controller', 'aws.controller',])
app.config_from_object('vimma.celeryconfig')
