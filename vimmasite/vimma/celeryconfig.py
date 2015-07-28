from celery.schedules import crontab
import os

_every_20s = 20
_every_1min = crontab(minute='*')
_every_5min = crontab(minute='*/5')
_every_1h = crontab(minute=0)

BROKER_URL = os.getenv('BROKER_URL', "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv('RESULT_BACKEND', "redis://localhost/0")

CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = CELERY_TASK_SERIALIZER
CELERY_ACCEPT_CONTENT = [CELERY_TASK_SERIALIZER,]

CELERYBEAT_SCHEDULE = {
    'update-all-vms-status': {
        'task': 'vimma.vmutil.update_all_vms_status',
        'schedule': _every_5min,
    },
    'dispatch-all-expiration-notifications': {
        'task': 'vimma.vmutil.dispatch_all_expiration_notifications',
        'schedule': _every_1h,
    },
    'dispatch-all-expiration-grace-end-actions': {
        'task': 'vimma.vmutil.dispatch_all_expiration_grace_end_actions',
        'schedule': _every_1h,
    },
}
