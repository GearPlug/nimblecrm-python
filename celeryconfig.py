from datetime import timedelta
from celery.schedules import crontab

# List of modules to import when celery starts.
CELERY_IMPORTS = ('apiconnector.celery',)

## Broker settings.
BROKER_URL = 'redis://localhost:6379/0'

## Using the database to store task state and results.
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

CELERYBEAT_SCHEDULE = {
    'update-plugs-1-minutes': {
        'task': 'apps.gp.tasks.update_gears',
        'schedule': timedelta(seconds=30, ),  # , seconds=30
    },
}

CELERY_TIMEZONE = 'UTC'

CELERY_ACCEPT_CONTENT = ['json', ]
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
