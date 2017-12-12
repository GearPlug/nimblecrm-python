from datetime import timedelta

# List of modules to import when celery starts.
CELERY_IMPORTS = ('apiconnector.celery',)

BROKER_URL = 'redis://localhost:6379'

CELERYBEAT_SCHEDULE = {
    'update-plugs-1-minutes': {
        'task': 'apps.gp.tasks.update_all_gears',
        'schedule': timedelta(seconds=30, ),
    },
}

CELERY_TIMEZONE = 'UTC'
CELERY_ACCEPT_CONTENT = ['json', ]
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# CELERYD_TASK_SOFT_TIME_LIMIT = 45