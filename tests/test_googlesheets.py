from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController
from apps.gp.models import Connection, ConnectorEnum, \
    GoogleSpreadSheetsConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, GoogleSpreadSheetsConnection, StoredData
from django.contrib.auth.models import User
from datetime import datetime
from django.test import TestCase, Client
from collections import OrderedDict
from apiclient import discovery
from apps.gp.map import MapField
import httplib2
import json
import os


class GoogleSpreadSheetsControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='test',
                                       email='lyrubiano5@gmail.com',
                                       password='Prueba#2017')
        _dict_user = {
            'user': cls.user,
            'connector_id': ConnectorEnum.GoogleSpreadSheets.value
        }

        cls.connection = Connection.objects.create(**_dict_user)

        credentials = json.loads(os.environ.get('TEST_GOOGLESHEETS_CREDENTIALS'))

        _dict_connection = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'credentials_json': credentials,
        }
        cls.googlesheets_connection = GoogleSpreadSheetsConnection.objects.create(
            **_dict_connection)

        action_source = Action.objects.get(
            connector_id=ConnectorEnum.GoogleSpreadSheets.value,
            action_type='source', name='get row',
            is_active=True)
        action_target = Action.objects.get(
            connector_id=ConnectorEnum.GoogleSpreadSheets.value,
            action_type='target', name='set row',
            is_active=True)

        _dict_plug_source = {
            'name': 'PlugTestSource',
            'connection': cls.connection,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**_dict_plug_source)

        _dict_plug_target = {
            'name': 'PlugTestTarget',
            'connection': cls.connection,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }

        cls.plug_target = Plug.objects.create(**_dict_plug_target)

        cls.specification1 = ActionSpecification.objects.get(
            action=action_source, name='spreadsheet')
        cls.specification2 = ActionSpecification.objects.get(
            action=action_source, name='worksheet')

        cls.specification3 = ActionSpecification.objects.get(
            action=action_target, name='spreadsheet')
        cls.specification4 = ActionSpecification.objects.get(
            action=action_target, name='worksheet')

        _dict_action_specification_source_1= {
            'plug': cls.plug_source,
            'action_specification': cls.specification1,
            'value': os.environ.get('TEST_GOOGLESHEETS_SHEET')
        }

        cls.plug_action_specificaion_source_1 = PlugActionSpecification.objects.create(
            **_dict_action_specification_source_1)

        _dict_action_specification_source_2 = {
            'plug': cls.plug_source,
            'action_specification': cls.specification2,
            'value': os.environ.get('TEST_GOOGLESHEETS_WORKSHEET')
        }

        cls.plug_action_specificaion_source_2 = PlugActionSpecification.objects.create(
            **_dict_action_specification_source_2)

        _dict_action_specification_target_1 = {
            'plug': cls.plug_target,
            'action_specification': cls.specification3,
            'value': os.environ.get('TEST_GOOGLESHEETS_SHEET')
        }

        cls.plug_action_specificaion_target_1 = PlugActionSpecification.objects.create(
            **_dict_action_specification_target_1)

        _dict_action_specification_target_2 = {
            'plug': cls.plug_target,
            'action_specification': cls.specification4,
            'value': os.environ.get('TEST_GOOGLESHEETS_WORKSHEET')
        }

        cls.plug_action_specificaion_target_2 = PlugActionSpecification.objects.create(
            **_dict_action_specification_target_2)

    def setUp(self):
        self.controller_source = GoogleSpreadSheetsController(
            self.plug_source.connection.related_connection, self.plug_source)
        self.controller_target = GoogleSpreadSheetsController(
            self.plug_target.connection.related_connection, self.plug_target)
        self._credentials= json.loads(os.environ.get('TEST_GOOGLESHEETS_CREDENTIALS'))

    def _get_sheet_id(self):
        id = ""
        result = self.controller_source.get_sheet_list()
        for i in result:
            if i['name'] == self.controller_source._spreadsheet_id:
                id = i['id']
        return id

    def test_controller(self):
        self.assertIsInstance(self.controller_source._connection_object,
                              GoogleSpreadSheetsConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertIsInstance(self.controller_target._plug, Plug)
        self.assertTrue(self.controller_source._credential)
        self.assertTrue(self.controller_target._credential)
        self.assertEqual(self.controller_source._spreadsheet_id, os.environ.get('TEST_GOOGLESHEETS_SHEET'))
        self.assertEqual(self.controller_target._spreadsheet_id, os.environ.get('TEST_GOOGLESHEETS_SHEET'))
        self.assertEqual(self.controller_source._worksheet_name, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))
        self.assertEqual(self.controller_target._worksheet_name, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))

    def test_test_connection(self):
        result_source = self.controller_source.test_connection()
        self.assertTrue(result_source)

    def test_column_string(self):
        result = self.controller_source.colnum_string(10)
        self.assertEqual(result, "J")

    def test_get_sheet_list(self):
        result = self.controller_source.get_sheet_list()
        sheet= ""
        for i in result:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_SHEET'):
                sheet=i['name']
        self.assertEqual(sheet,os.environ.get('TEST_GOOGLESHEETS_SHEET'))

    def test_get_worksheet_list(self):
        result = self.controller_source.get_sheet_list()
        for i in result:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_SHEET'):
                id = i['id']
        result = self.controller_source.get_worksheet_list(id)
        worksheet = ""
        for i in result:
            if i['title'] == os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'):
                worksheet = i['title']
        self.assertEqual(worksheet, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))

    def test_get_worksheet_values(self):
        self.controller_source._spreadsheet_id=self._get_sheet_id()
        result = self.controller_source.get_worksheet_values()
        self.assertEqual(result[0][0], os.environ.get('TEST_GOOGLESHEETS_FIRST_FIELD'))

    def test_get_worksheet_first_row(self):
        self.controller_source._spreadsheet_id=self._get_sheet_id()
        result = self.controller_source.get_worksheet_first_row()
        self.assertEqual(result[0], os.environ.get('TEST_GOOGLESHEETS_FIRST_FIELD'))

    def test_create_row(self):
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        self.controller_source._spreadsheet_id = self._get_sheet_id()
        self.controller_target.create_row(["test", "test"],2)
        result = self.controller_source.get_worksheet_values()
        self.assertEqual(result[1][0], "test")

    def test_get_target_fields(self):
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        result = self.controller_target.get_target_fields()
        self.assertEqual(result[0], os.environ.get('TEST_GOOGLESHEETS_FIRST_FIELD'))

    def test_get_mapping_fields(self):
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        result = self.controller_target.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_action_specification_options(self, **kwargs):
        action_specification_id = self.specification3.id
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        result_1 = self.controller_target.get_action_specification_options(action_specification_id)
        sheet = ""
        for i in result_1:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_SHEET'):
                sheet = i['name']
        action_specification_id = self.specification4.id
        kwargs.update({'sheet_id': self.controller_target._spreadsheet_id})
        result_2 = self.controller_target.get_action_specification_options(action_specification_id, **kwargs)
        worksheet = ""
        for i in result_2:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'):
                worksheet = i['name']
        self.assertIsInstance(result_1, tuple)
        self.assertIsInstance(result_2, tuple)
        self.assertEqual(sheet, os.environ.get('TEST_GOOGLESHEETS_SHEET'))
        self.assertEqual(worksheet, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))

    def test_download_to_stored_data(self):
        count1 = StoredData.objects.filter(connection=self.connection, plug=self.plug_source).count()
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        self.controller_source._spreadsheet_id = self._get_sheet_id()
        result = self.controller_source.get_worksheet_values()
        result.pop(0)
        count2 = 0
        for i in result:
            count2 = count2+len(i)
        self.controller_source.download_source_data()
        count3 = StoredData.objects.filter(connection=self.connection,plug=self.plug_source).count()
        self.assertEqual(count1+count2, count3)

    def test_send_stored_data(self):
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        self.controller_source._spreadsheet_id = self._get_sheet_id()
        result = self.controller_target.get_worksheet_first_row()
        target_fields = OrderedDict([(f, "%%{0}%%".format(f)) for f in result])
        data = {i : "valor" for i in result}
        source_data = [{'id':1, 'data':data}]
        self.controller_target.send_stored_data(source_data, target_fields, is_first=True)
        result = self.controller_source.get_worksheet_values()
        for i in result[-1]:
            self.assertEqual("valor",i)