import os
from celery import Celery
import celeryconfig
from django.conf import settings

# set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apiconnector.settings')
app = Celery('apiconnector')

# Using a string here means the worker will not have to
# pickle the object when using Windows.
app.config_from_object(celeryconfig)
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
