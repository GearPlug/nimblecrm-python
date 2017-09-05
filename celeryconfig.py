from datetime import timedelta

# List of modules to import when celery starts.
CELERY_IMPORTS = ('apiconnector.celery',)

# Broker settings
# BROKER_URL = 'sqs://AKIAIWBWN7I5X2OEKRAQ:nhLbsWGf74NNq+bKC49USY7b3bzsNLEClvVGRAYi@'
# BROKER_TRANSPORT_OPTIONS = {
#     # 'region': 'us-east-1',
#     'polling_interval': 60,
# }
BROKER_URL = 'redis://localhost:6379'

CELERY_DEFAULT_QUEUE = 'grplug0'
SQS_QUEUE_NAME = 'grplug0'

# Using the database to store task state and results.
# CELERY_RESULT_BACKEND = 'sqs://AKIAIWBWN7I5X2OEKRAQ:nhLbsWGf74NNq+bKC49USY7b3bzsNLEClvVGRAYi@'
CELERYBEAT_SCHEDULE = {
    'update-plugs-1-minutes': {
        'task': 'apps.gp.tasks.update_all_gears',
        'schedule': timedelta(seconds=40, ),  # , seconds=30
    },
}

CELERY_TIMEZONE = 'UTC'
CELERY_ACCEPT_CONTENT = ['json', ]
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
