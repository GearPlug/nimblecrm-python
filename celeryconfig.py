from datetime import timedelta

# List of modules to import when celery starts.
CELERY_IMPORTS = ('apiconnector.celery',)

## Broker settings.
# BROKER_URL = 'redis://localhost:6379/0'
BROKER_URL = 'amqp://gearplug:12357*_HoLa@192.168.10.210:5672//'
# BROKER_URL = 'amqp://gearplug:gearplug@192.168.10.210:5672//'

## Using the database to store task state and results.
# CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
# CELERY_RESULT_BACKEND = 'amqp://gearplug:gearplug@192.168.10.166:5672//'
# CELERY_RESULT_BACKEND = 'amqp://gearplug:gearplug@192.168.10.210:5672//'

CELERYBEAT_SCHEDULE = {
    'update-plugs-1-minutes': {
        'task': 'apps.gp.tasks.update_all_gears',
        'schedule': timedelta(seconds=15, ),  # , seconds=30
    },
    # 'update-plugs-1-minutes': {
    #     'task': 'apps.gp.tasks.update_gears',
    #     'schedule': timedelta(seconds=10, ),  # , seconds=30
    # },
}

CELERY_TIMEZONE = 'UTC'
CELERY_ACCEPT_CONTENT = ['json', ]
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
