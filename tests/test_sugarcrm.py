import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, SugarCRMConnection, Plug, Action, ActionSpecification, PlugActionSpecification, \
    Gear, GearMap, StoredData, GearMapData
from apps.history.models import DownloadHistory, SendHistory
from apps.gp.controllers.crm import SugarCRMController
from sugarcrm.client import Client as SugarCRMClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class SugarCRMControllerTestCases(TestCase):
    """Casos de prueba del controlador SugarCRM.

        Variables de entorno:
            TEST_SUGARCRM_URL: String: URL del servidor.
            TEST_SUGARCRM_CONNECTION_USER: String: Usuario.
            TEST_SUGARCRM_CONNECTION_PASSWORD: String: Contraseña.

    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
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
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        # self.client = Client()
        self.source_controller = SugarCRMController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = SugarCRMController(self.plug_target.connection.related_connection, self.plug_target)

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.source_controller._connection_object, SugarCRMConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.SugarCRM)
        self.assertIsInstance(self.source_controller._client, SugarCRMClient)

    def test_connection(self):
        """

        :return:
        """
        self.assertTrue(self.source_controller.test_connection())

    def test_get_available_modules(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.source_controller.get_available_modules()
        self.assertIn('modules', result)

    def test_get_entry_list(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.source_controller.get_entry_list('Leads')
        self.assertIsInstance(result, dict)

    def test_get_module_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.source_controller.get_module_fields('Leads')
        self.assertIsInstance(result, dict)

    def test_get_mapping_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.source_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_download_to_stored_data(self):
        """Comprueba que la llamada al metodo devuelva un diccionario y la existencia de los atributos necesarios y
        su respectivo tipo de dato almacenado como valor.

        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source)
        self.assertIsInstance(result, dict)
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
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection, self.plug_source)

        qs = StoredData.objects.order_by('object_id').values_list('object_id', flat=True).distinct()
        for lead in qs:
            count = DownloadHistory.objects.filter(identifier={'name': 'id', 'value': lead}).count()
            self.assertGreater(count, 0)

    def test_send_stored_data(self):
        """Guarda datos en StoredData y luego los envía la data mapeada al servidor CRM, luego comprueba de que
        el valor devuelto sea una lista además de comprobar que esté guardando registros en SendHistory.

        """
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
        entries = self.target_controller.send_target_data(source_data, target_fields, is_first=is_first)
        self.assertIsInstance(entries, list)

        for object_id in entries:
            count = SendHistory.objects.filter(identifier=object_id).count()
            self.assertGreater(count, 0)
