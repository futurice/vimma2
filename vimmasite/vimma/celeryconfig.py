from celery.schedules import crontab

_every_20s = 20
_every_1min = crontab(minute='*')
_every_5min = crontab(minute='*/5')

CELERYBEAT_SCHEDULE = {
    'update-all-vms-status': {
        'task': 'vimma.vmutil.update_all_vms_status',
        'schedule': _every_5min,
    },
}
