import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, MercadoLibreConnection, Plug, Action, Gear, GearMap, GearMapData, StoredData
from apps.history.models import DownloadHistory, SendHistory
from apps.gp.controllers.ecomerce import MercadoLibreController
from mercadolibre.client import Client as MercadoLibreClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class MercadolibreControllerTestCases(TestCase):
    """
       Variables de entorno:
           TEST_MERCADOLIBRE_TOKEN: String: Access Token.
           TEST_MERCADOLIBRE_USER_ID: String: ID de usuario.
           TEST_MERCADOLIBRE_SITE: String: Sitio.
           TEST_MERCADOLIBRE_APP_ID: String: Aplicación.
    """

    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.MercadoLibre.value
        }
        cls.connection_source = Connection.objects.create(**_dict_connection)

        _dict_mercadolibre_connection_source = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_MERCADOLIBRE_TOKEN'),
            'user_id': os.environ.get('TEST_MERCADOLIBRE_USER_ID'),
            'site': os.environ.get('TEST_MERCADOLIBRE_SITE'),

        }
        cls.mercadolibre_connection_source = MercadoLibreConnection.objects.create(
            **_dict_mercadolibre_connection_source)

        cls.connection_target = Connection.objects.create(**_dict_connection)

        _dict_mercadolibre_connection_target = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_MERCADOLIBRE_TOKEN'),
            'user_id': os.environ.get('TEST_MERCADOLIBRE_USER_ID'),
            'site': os.environ.get('TEST_MERCADOLIBRE_SITE'),

        }
        cls.mercadolibre_connection_target = MercadoLibreConnection.objects.create(
            **_dict_mercadolibre_connection_target)

        action_source = Action.objects.get(connector_id=ConnectorEnum.MercadoLibre.value, action_type='source',
                                           name='created_orders', is_active=True)

        _dict_mercadolibre_plug_source = {
            'name': 'PlugTest',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**_dict_mercadolibre_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.MercadoLibre.value, action_type='target',
                                           name='list product', is_active=True)

        _dict_mercadolibre_plug_target = {
            'name': 'PlugTest',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**_dict_mercadolibre_plug_target)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_1 = {'target_name': 'condition', 'source_value': 'used', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'currency_id', 'source_value': 'COP', 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'buying_mode', 'source_value': 'buy_it_now', 'gear_map': cls.gear_map}
        map_data_4 = {'target_name': 'warranty', 'source_value': '24 meses', 'gear_map': cls.gear_map}
        map_data_5 = {'target_name': 'category_id', 'source_value': 'MCO40932', 'gear_map': cls.gear_map}
        map_data_6 = {'target_name': 'title', 'source_value': '%%name%%', 'gear_map': cls.gear_map}
        map_data_7 = {'target_name': 'listing_type_id', 'source_value': 'free', 'gear_map': cls.gear_map}
        map_data_8 = {'target_name': 'available_quantity', 'source_value': '1', 'gear_map': cls.gear_map}
        map_data_9 = {'target_name': 'price', 'source_value': '10', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)
        GearMapData.objects.create(**map_data_4)
        GearMapData.objects.create(**map_data_5)
        GearMapData.objects.create(**map_data_6)
        GearMapData.objects.create(**map_data_7)
        GearMapData.objects.create(**map_data_8)
        GearMapData.objects.create(**map_data_9)

    def setUp(self):
        # self.client = Client()
        self.source_controller = MercadoLibreController(self.plug_source.connection.related_connection,
                                                        self.plug_source)
        self.target_controller = MercadoLibreController(self.plug_target.connection.related_connection,
                                                        self.plug_target)

        self.hook = {"resource": "/orders/1469747931", "user_id": os.environ.get('TEST_MERCADOLIBRE_USER_ID'),
                     "topic": "created_orders",
                     "application_id": os.environ.get('TEST_MERCADOLIBRE_APP_ID'), "attempts": 1,
                     "sent": "2017-09-06T15:43:17.717Z",
                     "received": "2017-09-06T15:43:17.700Z"}

    def test_controller(self):
        self.assertIsInstance(self.source_controller._connection_object, MercadoLibreConnection)
        self.assertIsInstance(self.target_controller._connection_object, MercadoLibreConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.MercadoLibre)
        self.assertIsInstance(self.source_controller._client, MercadoLibreClient)
        self.assertIsInstance(self.target_controller._client, MercadoLibreClient)

    def test_list_product(self):
        result = self.source_controller.get_target_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)

    def test_get_mapping_fields(self):
        result = self.source_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_me(self):
        result = self.source_controller.get_me()
        self.assertIsInstance(result, dict)

    def test_get_sites(self):
        result = self.source_controller.get_sites()
        self.assertIsInstance(result, list)

    def test_get_listing_types(self):
        result = self.source_controller.get_listing_types()
        self.assertIsInstance(result, list)

    def test_do_webhook_process(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.
        """
        result = self.source_controller.do_webhook_process(self.hook)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, event=self.hook)
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
        """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
        count_data = len(self.hook)
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source, event=self.hook)
        count_store = StoredData.objects.filter(connection=self.connection_source, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        self.assertEqual(count_data, count_store)
        self.assertEqual(history.identifier, str({'name': 'resource', 'value': self.hook['resource']}))

    def test_send_stored_data(self):
        """Guarda datos en StoredData y luego los envía la data mapeada al servidor CRM, luego comprueba de que
        el valor devuelto sea una lista además de comprobar que esté guardando registros en SendHistory.

        """
        result1 = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                              self.plug_source, event=self.hook)
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
