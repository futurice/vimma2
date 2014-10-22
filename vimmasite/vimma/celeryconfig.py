from celery.schedules import crontab

_every_20s = 20
_every_1min = crontab(minute='*')

CELERYBEAT_SCHEDULE = {
    'update-all-vms-status': {
        'task': 'vimma.vmutil.update_all_vms_status',
        'schedule': _every_20s,
    },
}
