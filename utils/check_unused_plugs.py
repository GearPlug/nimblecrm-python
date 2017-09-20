import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apiconnector.settings")
django.setup()
from apps.gp.models import Plug

sources = Plug.objects.filter(plug_type__iexact='source', gear_source__isnull=True)
targets = Plug.objects.filter(plug_type__iexact='target', gear_target__isnull=True)
print("sources: {}".format(len(sources)))
print("targets: {}".format(len(targets)))
