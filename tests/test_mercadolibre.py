from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, MercadoLibreConnection, Plug, Action
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

        token = {'expires_in': 21600, 'token_type': 'bearer', 'refresh_token': 'TG-59b16412e4b089ad60aee3ff-268958406',
                 'expires_at': 1504819315.0165474,
                 'access_token': 'APP_USR-1063986061828245-090711-8ccf0fb702e67077dde1166a4ce647b6__J_N__-268958406',
                 'user_id': 268958406, 'scope': 'offline_access read write'}

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'token': token,
            'user_id': 268958406,
            'site': 'MCO'

        }
        cls.mercadolibre_connection = MercadoLibreConnection.objects.create(**_dict2)

        action = Action.objects.get(connector_id=ConnectorEnum.MercadoLibre.value, action_type='target',
                                    name='list product', is_active=True)

        _dict3 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug = Plug.objects.create(**_dict3)

    def setUp(self):
        # self.client = Client()
        self.controller = MercadoLibreController(self.plug.connection.related_connection, self.plug)

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
