import os
import django
import timeit

#  you have to set the correct path to you settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apiconnector.settings")
django.setup()
from django.contrib.auth.models import User
from apps.gp.models import GearGroup, Gear

user_list = User.objects.all()
for u in user_list:
    group = GearGroup.objects.filter(user=u)
    if group is None:
        group = GearGroup.objects.create(name="default group", user=u)
    gear_list = Gear.objects.filter(user=u)
    for gear in gear_list:
        gear.gear_group = group
        gear.save(update_fields=['gear_group'])
