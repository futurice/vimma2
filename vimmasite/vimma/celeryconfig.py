CELERYBEAT_SCHEDULE = {
    'update-all-vms-status-every-5s': {
        'task': 'vimma.vmutil.update_all_vms_status',
        # can also be a Celery crontab
        'schedule': 5,
    },
}
