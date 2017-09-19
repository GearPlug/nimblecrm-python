import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, SugarCRMConnection, Plug, Action, ActionSpecification, PlugActionSpecification, \
    Gear, GearMap, StoredData, GearMapData
from apps.gp.controllers.crm import SugarCRMController
from sugarcrm.client import Client as SugarCRMClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class SugarCRMControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.SugarCRM.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        sugarcrm_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'url': os.environ.get('TEST_SUGARCRM_URL'),
            'connection_user': os.environ.get('TEST_SUGARCRM_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_SUGARCRM_CONNECTION_PASSWORD')
        }
        cls.sugarcrm_connection1 = SugarCRMConnection.objects.create(**sugarcrm_connection1)

        cls.connection_target = Connection.objects.create(**connection)

        sugarcrm_connection2 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'url': os.environ.get('TEST_SUGARCRM_URL'),
            'connection_user': os.environ.get('TEST_SUGARCRM_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_SUGARCRM_CONNECTION_PASSWORD')
        }
        cls.sugarcrm_connection2 = SugarCRMConnection.objects.create(**sugarcrm_connection2)

        action_source = Action.objects.get(connector_id=ConnectorEnum.SugarCRM.value, action_type='source',
                                           name='get module data', is_active=True)

        sugarcrm_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_source = Plug.objects.create(**sugarcrm_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.SugarCRM.value, action_type='target',
                                           name='set module data', is_active=True)

        sugarcrm_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_target = Plug.objects.create(**sugarcrm_plug_target)

        specification1 = ActionSpecification.objects.get(action=action_source, name='module')
        specification2 = ActionSpecification.objects.get(action=action_target, name='module')

        action_specification1 = {
            'plug': cls.plug_source,
            'action_specification': specification1,
            'value': 'Leads'
        }
        PlugActionSpecification.objects.create(**action_specification1)

        action_specification2 = {
            'plug': cls.plug_target,
            'action_specification': specification2,
            'value': 'Leads'
        }
        PlugActionSpecification.objects.create(**action_specification2)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_2 = {'target_name': 'name', 'source_value': '%%name%%', 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'webtolead_email_opt_out', 'source_value': False, 'gear_map': cls.gear_map}
        map_data_4 = {'target_name': 'converted', 'source_value': False, 'gear_map': cls.gear_map}
        map_data_5 = {'target_name': 'email_opt_out', 'source_value': False, 'gear_map': cls.gear_map}
        map_data_6 = {'target_name': 'deleted', 'source_value': False, 'gear_map': cls.gear_map}
        map_data_7 = {'target_name': 'webtolead_invalid_email', 'source_value': False, 'gear_map': cls.gear_map}
        map_data_8 = {'target_name': 'email2', 'source_value': '%%email2%%', 'gear_map': cls.gear_map}
        map_data_9 = {'target_name': 'invalid_email', 'source_value': False, 'gear_map': cls.gear_map}
        map_data_10 = {'target_name': 'do_not_call', 'source_value': False, 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)
        GearMapData.objects.create(**map_data_4)
        GearMapData.objects.create(**map_data_5)
        GearMapData.objects.create(**map_data_6)
        GearMapData.objects.create(**map_data_7)
        GearMapData.objects.create(**map_data_8)
        GearMapData.objects.create(**map_data_9)
        GearMapData.objects.create(**map_data_10)

    def setUp(self):
        # self.client = Client()
        self.source_controller = SugarCRMController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = SugarCRMController(self.plug_target.connection.related_connection, self.plug_target)

    def test_controller(self):
        self.assertIsInstance(self.source_controller._connection_object, SugarCRMConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.SugarCRM)
        self.assertIsInstance(self.source_controller._client, SugarCRMClient)

    def test_get_available_modules(self):
        result = self.source_controller.get_available_modules()
        self.assertIn('modules', result)

    def test_get_entry_list(self):
        result = self.source_controller.get_entry_list('Leads')
        self.assertIsInstance(result, dict)

    def test_get_module_fields(self):
        result = self.source_controller.get_module_fields('Leads')
        self.assertIsInstance(result, dict)

    def test_get_mapping_fields(self):
        result = self.source_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_download_to_stored_data(self):
        connection = self.source_controller._connection_object.connection
        plug = self.source_controller._plug

        result1 = self.source_controller.download_source_data()
        self.assertTrue(result1)
        count1 = StoredData.objects.filter(connection=connection, plug=plug).count()

        result2 = self.source_controller.download_source_data()
        self.assertFalse(result2)
        count2 = StoredData.objects.filter(connection=connection, plug=plug).count()

        self.assertEqual(count1, count2)

    def test_send_stored_data(self):
        result1 = self.source_controller.download_source_data()
        self.assertIsNotNone(result1)
        query_params = {'connection': self.gear.source.connection, 'plug': self.gear.source}
        is_first = self.gear_map.last_sent_stored_data_id is None
        if not is_first:
            query_params['id__gt'] = self.gear.gear_map.last_sent_stored_data_id
        stored_data = StoredData.objects.filter(**query_params)
        target_fields = OrderedDict(
            (data.target_name, data.source_value) for data in GearMapData.objects.filter(gear_map=self.gear_map))
        source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}} for
                       item in stored_data.values_list('object_id').distinct()]
        entries = self.target_controller.send_stored_data(source_data, target_fields, is_first=is_first)
        self.assertIsInstance(entries, list)
