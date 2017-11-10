from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController
from apps.gp.models import Connection, ConnectorEnum, Action, Plug, ActionSpecification, PlugActionSpecification, \
    GoogleSpreadSheetsConnection, StoredData, Gear, GearMap, GearMapData
from apps.history.models import DownloadHistory, SendHistory
from django.contrib.auth.models import User
from django.test import TestCase, Client
from collections import OrderedDict
from apps.gp.map import MapField
import json
import os


class GoogleSpreadSheetsControllerTestCases(TestCase):
    """Casos de prueba del controlador Google Spreadsheets.

        Variables de entorno:
            TEST_GOOGLESHEETS_CREDENTIALS: String: Token generado a partir de oAuth.
            TEST_GOOGLESHEETS_SHEET: String: Nombre del spreadsheet.
            TEST_GOOGLESHEETS_WORKSHEET: String: Nombre de la hoja.
            TEST_GOOGLESHEETS_FIRST_FIELD: String: Primer field.

    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
        cls.user = User.objects.create(username='test', email='lyrubiano5@gmail.com', password='Prueba#2017')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.GoogleSpreadSheets.value
        }

        cls.connection_source = Connection.objects.create(**connection)

        credentials = json.loads(os.environ.get('TEST_GOOGLESHEETS_CREDENTIALS'))

        googlesheets_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'credentials_json': credentials,
        }
        cls.googlesheets_connection1 = GoogleSpreadSheetsConnection.objects.create(**googlesheets_connection1)

        cls.connection_target = Connection.objects.create(**connection)

        googlesheets_connection2 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'credentials_json': credentials,
        }
        cls.googlesheets_connection2 = GoogleSpreadSheetsConnection.objects.create(**googlesheets_connection2)

        action_source = Action.objects.get(connector_id=ConnectorEnum.GoogleSpreadSheets.value, action_type='source',
                                           name='get row', is_active=True)

        googlesheets_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**googlesheets_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.GoogleSpreadSheets.value, action_type='target',
                                           name='set row', is_active=True)

        _dict_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }

        cls.plug_target = Plug.objects.create(**_dict_plug_target)

        cls.specification1 = ActionSpecification.objects.get(action=action_source, name='spreadsheet')
        cls.specification2 = ActionSpecification.objects.get(action=action_source, name='worksheet')

        cls.specification3 = ActionSpecification.objects.get(action=action_target, name='spreadsheet')
        cls.specification4 = ActionSpecification.objects.get(action=action_target, name='worksheet')

        action_specification1 = {
            'plug': cls.plug_source,
            'action_specification': cls.specification1,
            'value': os.environ.get('TEST_GOOGLESHEETS_SHEET')
        }
        PlugActionSpecification.objects.create(**action_specification1)

        action_specification2 = {
            'plug': cls.plug_source,
            'action_specification': cls.specification2,
            'value': os.environ.get('TEST_GOOGLESHEETS_WORKSHEET')
        }
        PlugActionSpecification.objects.create(**action_specification2)

        action_specification3 = {
            'plug': cls.plug_target,
            'action_specification': cls.specification3,
            'value': os.environ.get('TEST_GOOGLESHEETS_SHEET')
        }
        PlugActionSpecification.objects.create(**action_specification3)

        action_specification4 = {
            'plug': cls.plug_target,
            'action_specification': cls.specification4,
            'value': os.environ.get('TEST_GOOGLESHEETS_WORKSHEET')
        }
        PlugActionSpecification.objects.create(**action_specification4)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_1 = {'target_name': 'nombre', 'source_value': '%%nombre%%', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'apellido', 'source_value': '%%apellido%%', 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'email', 'source_value': '%%email%%', 'gear_map': cls.gear_map}
        map_data_4 = {'target_name': 'telefono', 'source_value': '%%telefono%%', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)
        GearMapData.objects.create(**map_data_4)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        self.controller_source = GoogleSpreadSheetsController(self.plug_source.connection.related_connection,
                                                              self.plug_source)
        self.controller_target = GoogleSpreadSheetsController(self.plug_target.connection.related_connection,
                                                              self.plug_target)
        self._credentials = json.loads(os.environ.get('TEST_GOOGLESHEETS_CREDENTIALS'))

    def _get_sheet_id(self):
        id = ''
        result = self.controller_source.get_sheet_list()
        for i in result:
            if i['name'] == self.controller_source._spreadsheet_id:
                id = i['id']
        return id

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.controller_source._connection_object, GoogleSpreadSheetsConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertIsInstance(self.controller_target._plug, Plug)
        self.assertTrue(self.controller_source._credential)
        self.assertTrue(self.controller_target._credential)
        self.assertEqual(self.controller_source._spreadsheet_id, os.environ.get('TEST_GOOGLESHEETS_SHEET'))
        self.assertEqual(self.controller_target._spreadsheet_id, os.environ.get('TEST_GOOGLESHEETS_SHEET'))
        self.assertEqual(self.controller_source._worksheet_name, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))
        self.assertEqual(self.controller_target._worksheet_name, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))

    def test_test_connection(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result_source = self.controller_source.test_connection()
        self.assertTrue(result_source)

    def test_column_string(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.colnum_string(10)
        self.assertEqual(result, 'J')

    def test_get_sheet_list(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_sheet_list()
        sheet = ''
        for i in result:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_SHEET'):
                sheet = i['name']
        self.assertEqual(sheet, os.environ.get('TEST_GOOGLESHEETS_SHEET'))

    def test_get_worksheet_list(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_sheet_list()
        for i in result:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_SHEET'):
                _id = i['id']
        result = self.controller_source.get_worksheet_list(_id)
        worksheet = ''
        for i in result:
            if i['title'] == os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'):
                worksheet = i['title']
        self.assertEqual(worksheet, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))

    def test_get_worksheet_values(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        self.controller_source._spreadsheet_id = self._get_sheet_id()
        result = self.controller_source.get_worksheet_values()
        self.assertEqual(result[0][0], os.environ.get('TEST_GOOGLESHEETS_FIRST_FIELD'))

    def test_get_worksheet_first_row(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        self.controller_source._spreadsheet_id = self._get_sheet_id()
        result = self.controller_source.get_worksheet_first_row()
        self.assertEqual(result[0], os.environ.get('TEST_GOOGLESHEETS_FIRST_FIELD'))

    def test_create_row(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        self.controller_source._spreadsheet_id = self._get_sheet_id()
        self.controller_target.create_row(['test', 'test'], 2)
        result = self.controller_source.get_worksheet_values()
        self.assertEqual(result[1][0], 'test')

    def test_get_target_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        result = self.controller_target.get_target_fields()
        self.assertEqual(result[0], os.environ.get('TEST_GOOGLESHEETS_FIRST_FIELD'))

    def test_get_mapping_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        result = self.controller_target.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_action_specification_options(self, **kwargs):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        action_specification_id = self.specification3.id
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        result_1 = self.controller_target.get_action_specification_options(action_specification_id)
        sheet = ''
        for i in result_1:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_SHEET'):
                sheet = i['name']
        action_specification_id = self.specification4.id
        kwargs.update({'sheet_id': self.controller_target._spreadsheet_id})
        result_2 = self.controller_target.get_action_specification_options(action_specification_id, **kwargs)
        worksheet = ''
        for i in result_2:
            if i['name'] == os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'):
                worksheet = i['name']
        self.assertIsInstance(result_1, tuple)
        self.assertIsInstance(result_2, tuple)
        self.assertEqual(sheet, os.environ.get('TEST_GOOGLESHEETS_SHEET'))
        self.assertEqual(worksheet, os.environ.get('TEST_GOOGLESHEETS_WORKSHEET'))

    def test_download_to_stored_data(self):
        """Comprueba que la llamada al metodo devuelva un diccionario y la existencia de los atributos necesarios y
        su respectivo tipo de dato almacenado como valor.

        """
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        self.controller_source._spreadsheet_id = self._get_sheet_id()

        result = self.controller_source.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source)
        self.assertIn('downloaded_data', result)
        self.assertIsInstance(result['downloaded_data'], list)
        self.assertIsInstance(result['downloaded_data'][-1], dict)
        self.assertIn('identifier', result['downloaded_data'][-1])
        self.assertIsInstance(result['downloaded_data'][-1]['identifier'], dict)
        self.assertIn('name', result['downloaded_data'][-1]['identifier'])
        self.assertIn('value', result['downloaded_data'][-1]['identifier'])
        self.assertIsInstance(result['downloaded_data'][-1], dict)
        self.assertIn('raw', result['downloaded_data'][-1])
        self.assertIsInstance(result['downloaded_data'][-1]['raw'], dict)
        self.assertIn('is_stored', result['downloaded_data'][-1])
        self.assertIsInstance(result['downloaded_data'][-1]['is_stored'], bool)
        self.assertIn('last_source_record', result)
        self.assertIsNotNone(result['last_source_record'])

    def test_download_source_data(self):
        """Comprueba que la llamada al metodo haya guardado data en StoredData y que se hayan creado registros de
        historial.

        """
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        self.controller_source._spreadsheet_id = self._get_sheet_id()

        result = self.controller_source.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source)

        qs = StoredData.objects.order_by('object_id').values_list('object_id', flat=True).distinct()
        for row in qs:
            count = DownloadHistory.objects.filter(identifier={'name': 'id', 'value': int(row)}).count()
            self.assertGreater(count, 0)

    def test_send_stored_data(self):
        """Guarda datos en StoredData y luego los envía la data mapeada al servidor Google, luego comprueba de que
        el valor devuelto sea una lista además de comprobar que esté guardando registros en SendHistory.

        """
        self.controller_target._spreadsheet_id = self._get_sheet_id()
        self.controller_source._spreadsheet_id = self._get_sheet_id()

        result1 = self.controller_source.download_source_data()
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
        entries = self.controller_target.send_target_data(source_data, target_fields, is_first=is_first)
        self.assertIsInstance(entries, list)

        for object_id in entries:
            count = SendHistory.objects.filter(identifier=object_id).count()
            self.assertGreater(count, 0)
