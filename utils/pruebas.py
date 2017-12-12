import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "apiconnector.settings")
django.setup()
# from apps.gp.models import Connector, Action, ActionSpecification
#
# def check_connector(connector_name):
#     connector = Connector.objects.get(name__iexact=connector_name)
#     actions = Action.objects.filter(connector=connector).prefetch_related('action_specification')
#     print("CONNECTOR: {0}".format(connector))
#     for action in actions:
#         print("\tACTION->  ID: {0}\t| NAME: '{1}' | TYPE: '{2}'.".format(action.id, action.name, action.action_type))
#         for specification in action.action_specification.all():
#             print("\t\tACTION SPECIFICATION->  ID: {0}\t| NAME '{1}'.".format(specification.id, specification.name))
#         if not action.action_specification.all():
#             print("\t\tNO ACTION SPECIFICATIONS.")
# check_connector('gmail')

# from apps.gp.models import StoredData, Gear, GearMapData
# from collections import OrderedDict
# from apps.gp.controllers.utils import get_dict_with_source_data as gd
#
# gear = Gear.objects.get(source_id=130)
# data = StoredData.objects.filter(plug_id=130, connection_id=4)
# source_data = [{'id': item[0], 'data': {i.name: i.value for i in data.filter(object_id=item[0])}} for item in data.values_list('object_id').distinct()]
# target_fields = OrderedDict((data.target_name, data.source_value) for data in GearMapData.objects.filter(gear_map=gear.gear_map))
# gd(source_data,target_fields)
