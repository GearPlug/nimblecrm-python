from apps.gp.controllers.lead import GoogleFormsController
from apps.gp.models import Connection, ConnectorEnum, Action, Plug, ActionSpecification, PlugActionSpecification, \
    GoogleFormsConnection, StoredData, Gear
from apps.history.models import DownloadHistory
from django.contrib.auth.models import User
from django.test import TestCase, Client
import json
import os


class GoogleFormsControllerTestCases(TestCase):
    """Casos de prueba del controlador Google Forms.

        Variables de entorno:
            TEST_GOOGLEFORMS_CREDENTIALS: String: Token generado a partir de oAuth.
            TEST_GOOGLEFORMS_SHEET: String: Nombre del spreadsheet.
            TEST_GOOGLEFORMS_FIRST_FIELD: String: Primera campo.
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
        cls.user = User.objects.create(username='test', email='lyrubiano5@gmail.com', password='Prueba#2017')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.GoogleForms.value
        }

        cls.connection_source = Connection.objects.create(**connection)

        cls.credentials = json.loads(os.environ.get('TEST_GOOGLEFORMS_CREDENTIALS'))

        googleforms_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'credentials_json': cls.credentials,
        }
        cls.googleforms_connection1 = GoogleFormsConnection.objects.create(**googleforms_connection1)

        action_source = Action.objects.get(connector_id=ConnectorEnum.GoogleForms.value, action_type='source',
                                           name='get answer', is_active=True)

        googleforms_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**googleforms_plug_source)

        cls.specification1 = ActionSpecification.objects.get(action=action_source, name='form')

        action_specification1 = {
            'plug': cls.plug_source,
            'action_specification': cls.specification1,
            'value': os.environ.get('TEST_GOOGLEFORMS_SHEET')
        }
        PlugActionSpecification.objects.create(**action_specification1)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        self.controller_source = GoogleFormsController(self.plug_source.connection.related_connection,
                                                       self.plug_source)

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
        self.assertIsInstance(self.controller_source._connection_object, GoogleFormsConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertTrue(self.controller_source._credential)
        self.assertEqual(self.controller_source._spreadsheet_id, os.environ.get('TEST_GOOGLEFORMS_SHEET'))

    def test_test_connection(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result_source = self.controller_source.test_connection()
        self.assertTrue(result_source)

    def test_get_sheet_list(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_sheet_list()
        sheet = ''
        for i in result:
            if i['id'] == os.environ.get('TEST_GOOGLEFORMS_SHEET'):
                sheet = i['id']
        self.assertEqual(sheet, os.environ.get('TEST_GOOGLEFORMS_SHEET'))

    def test_get_worksheet_values(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_worksheet_values()
        self.assertEqual(result[0][0], os.environ.get('TEST_GOOGLEFORMS_FIRST_FIELD'))

    def test_get_worksheet_first_row(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_worksheet_first_row()
        self.assertEqual(result[0], os.environ.get('TEST_GOOGLEFORMS_FIRST_FIELD'))

    def test_get_target_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_target_fields()
        self.assertEqual(result[0], os.environ.get('TEST_GOOGLEFORMS_FIRST_FIELD'))

    def test_download_to_stored_data(self):
        """Comprueba que la llamada al metodo devuelva un diccionario y la existencia de los atributos necesarios y
        su respectivo tipo de dato almacenado como valor.

        """
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
        result = self.controller_source.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source)

        qs = StoredData.objects.order_by('object_id').values_list('object_id', flat=True).distinct()
        for row in qs:
            count = DownloadHistory.objects.filter(identifier={'name': 'id', 'value': int(row)}).count()
            self.assertGreater(count, 0)
