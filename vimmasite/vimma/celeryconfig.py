from celery.schedules import crontab

_every_20s = 20
_every_1min = crontab(minute='*')
_every_5min = crontab(minute='*/5')
_every_1h = crontab(minute=0)

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
