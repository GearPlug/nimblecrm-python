from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, SugarCRMConnection, Plug, Action, ActionSpecification, PlugActionSpecification
from apps.gp.controllers.crm import SugarCRMController
from sugarcrm.client import Client as SugarCRMClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField


class SugarCRMControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.SugarCRM.value
        }
        cls.connection = Connection.objects.create(**_dict)

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'url': 'http://50.112.8.136/uat/uat/',
            'connection_user': 'admin2',
            'connection_password': '1q2w3e4r'

        }
        cls.sugarcrm_connection = SugarCRMConnection.objects.create(**_dict2)

        action = Action.objects.get(connector_id=ConnectorEnum.SugarCRM.value, action_type='source',
                                    name='get module data', is_active=True)

        _dict3 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug = Plug.objects.create(**_dict3)

        specification1 = ActionSpecification.objects.get(action=action, name='module')

        _dict4 = {
            'plug': cls.plug,
            'action_specification': specification1,
            'value': 'Leads'
        }
        PlugActionSpecification.objects.create(**_dict4)

    def setUp(self):
        # self.client = Client()
        self.controller = SugarCRMController(self.plug.connection.related_connection, self.plug)

    def test_controller(self):
        self.assertIsInstance(self.controller._connection_object, SugarCRMConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.SugarCRM)
        self.assertIsInstance(self.controller._client, SugarCRMClient)

    def test_get_available_modules(self):
        result = self.controller.get_available_modules()
        self.assertIn('modules', result)

    def test_get_entry_list(self):
        result = self.controller.get_entry_list('Leads')
        self.assertIsInstance(result, dict)

    def test_get_module_fields(self):
        result = self.controller.get_module_fields('Leads')
        self.assertIsInstance(result, dict)

    def test_get_mapping_fields(self):
        result = self.controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)