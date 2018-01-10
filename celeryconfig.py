from datetime import timedelta

CELERY_IMPORTS = ('apiconnector.celery',)

BROKER_URL = 'redis://localhost:6379'

CELERYBEAT_SCHEDULE = {
    'update-plugs-1-minutes': {
        'task': 'apps.gp.tasks.dispatch_all_gears',
        'schedule': timedelta(seconds=45, ),
        'options': {'queue': 'dispatch'},
    },
}

CELERY_TIMEZONE = 'UTC'
CELERY_ACCEPT_CONTENT = ['json', ]
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
