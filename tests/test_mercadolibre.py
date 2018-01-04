import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, MercadoLibreConnection, Plug, Action, \
    ActionSpecification, PlugActionSpecification, Gear, StoredData
from apps.history.models import DownloadHistory
from apps.gp.controllers.ecomerce import MercadoLibreController
from mercadolibre.client import Client as MercadoLibreClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField


class MercadolibreControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.MercadoLibre.value
        }
        cls.connection = Connection.objects.create(**_dict)

        token = os.environ.get('TEST_MERCADOLIBRE_TOKEN')

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'token': token,
            'user_id': 268958406,
            'site': 'MCO'

        }
        cls.mercadolibre_connection = MercadoLibreConnection.objects.create(**_dict2)

        action = Action.objects.get(
            connector_id=ConnectorEnum.MercadoLibre.value,
            action_type='source',
            name='created_orders', is_active=True)

        _dict3 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug = Plug.objects.create(**_dict3)

        _dict4 = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict4)

    def setUp(self):
        # self.client = Client()
        self.controller = MercadoLibreController(self.plug.connection.related_connection, self.plug)

        self.hook = {"resource": "/orders/1469747931", "user_id": 268958406,
                     "topic": "created_orders",
                     "application_id": 1063986061828245, "attempts": 1,
                     "sent": "2017-09-06T15:43:17.717Z",
                     "received": "2017-09-06T15:43:17.700Z"}

    def test_controller(self):
        self.assertIsInstance(self.controller._connection_object, MercadoLibreConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.MercadoLibre)
        self.assertIsInstance(self.controller._client, MercadoLibreClient)

    def test_list_product(self):
        result = self.controller.get_target_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)

    def test_get_mapping_fields(self):
        result = self.controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_me(self):
        result = self.controller.get_me()
        self.assertIsInstance(result, dict)

    def test_get_sites(self):
        result = self.controller.get_sites()
        self.assertIsInstance(result, list)

    def test_get_listing_types(self):
        result = self.controller.get_listing_types()
        self.assertIsInstance(result, list)

    def test_do_webhook_process(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.
        """
        result = self.controller.do_webhook_process(self.hook)
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
        result = self.controller.download_to_stored_data(self.plug.connection.related_connection, self.plug,
                                                         event=self.hook)
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
        result = self.controller.download_source_data(self.plug.connection.related_connection, self.plug, event=self.hook)
        count_store = StoredData.objects.filter(connection=self.connection, plug=self.plug).count()
        history = DownloadHistory.objects.last()
        self.assertEqual(count_data, count_store)
        self.assertEqual(history.identifier, str({'name': 'resource', 'value': self.hook['resource']}))

    # def test_send_stored_data(self):
    #     """Simula un dato de entrada (self._data), y verifica que retorne una lista de acuerdo a los parámetros establecidos
    #     """
    #     data_list = [OrderedDict(self._data())]
    #     result = self.target_controller.send_stored_data(data_list)
    #     self.assertIsInstance(result, list)
    #     self.assertIsInstance(result[-1], dict)
    #     self.assertIn('data', result[-1])
    #     self.assertIn('response', result[-1])
    #     self.assertIn('sent', result[-1])
    #     self.assertIn('identifier', result[-1])
    #     self.assertIsInstance(result[-1]['data'], dict)
    #     self.assertIsInstance(result[-1]['response'], str)
    #     self.assertIsInstance(result[-1]['sent'], bool)
    #     self.assertEqual(result[-1]['data'], dict(data_list[0]))
    #     result_view = self.target_controller.view_issue(result[-1]['identifier'])
    #     self.assertEqual(result_view['id'], result[-1]['identifier'])
    #     self.target_controller.delete_issue(result[-1]['identifier'])
