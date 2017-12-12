import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apiconnector.settings")
django.setup()
from apps.gp.models import Connector, Action, ActionSpecification

# actessentials = Connector.objects.get(name__iexact="actessentials")
#
# action = Action.objects.create(connector=actessentials, name='new opportunity', description="new opportunity",
#                                is_active=True, action_type='source')
# action2 = Action.objects.create(connector=actessentials, name='new contact', description="new contact", is_active=True,
#                                 action_type='source')
# action3 = Action.objects.create(connector=actessentials, name='create opportunity', description="create opportunity",
#                                 is_active=True, action_type='target')
# action4 = Action.objects.create(connector=actessentials, name='create contact', description="create contact",
#                                 is_active=True, action_type='target')
# connector = Connector.objects.get(name__iexact="Batchbook")
# source_action = Action.objects.create(name='new contact', description="new contact", is_active=True, connector=connector, action_type='source')
# target_action = Action.objects.create(name='create contact', description="create contact", is_active=True, connector=connector, action_type='target')
connector = Connector.objects.get(name__iexact="odoocrm")
a1 = Action.objects.create(name='create_contact', connector=connector, action_type='target')
a2 = Action.objects.create(name='new_contact', connector=connector, action_type='source')