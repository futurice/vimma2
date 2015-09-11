from celery import Celery


app = Celery(include=['vimma.vmutil', 'dummy.tasks', 'aws.tasks',])
app.config_from_object('vimma.celeryconfig')
