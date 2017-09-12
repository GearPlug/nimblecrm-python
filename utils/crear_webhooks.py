import os
import django
import timeit

#  you have to set the correct path to you settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apiconnector.settings")
django.setup()
# setup ="""
from apps.gp.models import Plug
from apps.gp.enum import ConnectorEnum

connector = ConnectorEnum.FacebookLeads
controller_class = ConnectorEnum.get_controller(connector)

plugs = Plug.objects.filter(
    connection__connector__name__iexact='facebookleads',
    connection__connector__action__name__iexact='get leads')
for plug in plugs:
    print("\n {}".format(plug))
    controller = controller_class(
        connection=plug.connection.related_connection, plug=plug)
    try:
        plug.webhook
    except AttributeError:
        try:
            controller.create_webhook()
            print("se creo el hook")
        except:
            plug.is_active = False
    try:
        print(plug.webhook)
    except:
        print("no hook")
# """
# a = timeit.Timer(setup=setup).repeat(7, 1000)
# print(min(a))
