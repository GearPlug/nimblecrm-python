from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController
from apps.gp.models import Connection, ConnectorEnum, \
    GoogleSpreadSheetsConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, \
    GoogleSpreadSheetsConnection
from django.contrib.auth.models import User
from django.test import TestCase, Client
import json
import os


class GoogleSpreadSheetsControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='test',
                                       email='lyrubiano5@gmail.com',
                                       password='Prueba#2017')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.GoogleSpreadSheets.value
        }

        cls.connection = Connection.objects.create(**_dict)

        credentials = json.loads(os.environ.get('credentials'))

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'credentials_json': credentials,
        }
        cls.googlesheets_connection = GoogleSpreadSheetsConnection.objects.create(
            **_dict2)

        action_source = Action.objects.get(
            connector_id=ConnectorEnum.GoogleSpreadSheets.value,
            action_type='source', name='get row',
            is_active=True)
        action_target = Action.objects.get(
            connector_id=ConnectorEnum.GoogleSpreadSheets.value,
            action_type='target', name='set row',
            is_active=True)

        _dict3 = {
            'name': 'PlugTestSource',
            'connection': cls.connection,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**_dict3)

        _dict4 = {
            'name': 'PlugTestTarget',
            'connection': cls.connection,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }

        cls.plug_target = Plug.objects.create(**_dict4)

        cls.specification1 = ActionSpecification.objects.get(
            action=action_source, name='spreadsheet')
        cls.specification2 = ActionSpecification.objects.get(
            action=action_source, name='worksheet')

        cls.specification3 = ActionSpecification.objects.get(
            action=action_target, name='spreadsheet')
        cls.specification4 = ActionSpecification.objects.get(
            action=action_target, name='worksheet')

        _dict5 = {
            'plug': cls.plug_source,
            'action_specification': cls.specification1,
            'value': os.environ.get('sheet')
        }

        cls.plug_action_specificaion_source_1 = PlugActionSpecification.objects.create(
            **_dict5)

        _dict6 = {
            'plug': cls.plug_source,
            'action_specification': cls.specification2,
            'value': os.environ.get('worksheet')
        }

        cls.plug_action_specificaion_source_1 = PlugActionSpecification.objects.create(
            **_dict6)

        _dict7 = {
            'plug': cls.plug_target,
            'action_specification': cls.specification3,
            'value': os.environ.get('sheet')
        }

        cls.plug_action_specificaion_source_1 = PlugActionSpecification.objects.create(
            **_dict7)

        _dict8 = {
            'plug': cls.plug_target,
            'action_specification': cls.specification4,
            'value': os.environ.get('worksheet')
        }

        cls.plug_action_specificaion_source_1 = PlugActionSpecification.objects.create(
            **_dict8)

    def setUp(self):
        self.controller_source = GoogleSpreadSheetsController(
            self.plug_source.connection.related_connection, self.plug_source)
        self.controller_target = GoogleSpreadSheetsController(
            self.plug_target.connection.related_connection, self.plug_target)
        self._credentials= json.loads(os.environ.get('credentials'))


    def test_controller(self):
        self.assertIsInstance(self.controller_source._connection_object,
                              GoogleSpreadSheetsConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertIsInstance(self.controller_target._plug, Plug)
        self.assertTrue(self.controller_source._credential)
        self.assertTrue(self.controller_target._credential)
        self.assertEqual(self.controller_source._spreadsheet_id, os.environ.get('sheet'))
        self.assertEqual(self.controller_target._spreadsheet_id, os.environ.get('sheet'))
        self.assertEqual(self.controller_source._worksheet_name, os.environ.get('worksheet'))
        self.assertEqual(self.controller_target._worksheet_name, os.environ.get('worksheet'))

    def test_test_connection(self):
        result_source = self.controller_source.test_connection()
        result_target = self.controller_source.test_connection()
        self.assertTrue(result_source)
        self.assertTrue(result_target)

    def test_refresh_token(self):
        self._connection_object.credentials_json = self._credential.to_json()
        self._connection_object.save()







        # def test_get_target_fields(self):
        #     result=self.controller.get_target_fields()
        #     self.assertEqual(result, self._get_fields())
        #
        # def test_get_mapping_fields(self):
        #     result=self.controller.get_mapping_fields()
        #     self.assertIsInstance(result, list)
        #     self.assertIsInstance(result[0], MapField)
        #
        # def test_get_action_specification_options(self):
        #     action_specification_id=self.specification.id
        #     result = self.controller.get_action_specification_options(action_specification_id)
        #     listss = tuple({'id': c['id'], 'name': c['name']} for c in self._client.get_lists()['lists'])
        #     self.assertIsInstance(result, tuple)
        #     self.assertEqual(result, listss)
