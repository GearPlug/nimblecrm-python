import json
import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.shortcuts import HttpResponse
from apps.gp.models import Connection, FacebookLeadsConnection, Plug, Action, ActionSpecification, \
    PlugActionSpecification, Gear, StoredData, GearMap, DownloadHistory
from apps.gp.controllers.lead import FacebookLeadsController
from facebookmarketing.client import Client as FacebookClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField


class FacebookControllerTestCases(TestCase):
    """Casos de prueba del controlador Facebook Leads.

    Variables de entorno:
        TEST_FACEBOOK_TOKEN: String: Token generado a partir de oAuth.
        TEST_FACEBOOK_PAGE: Int: Página la cual tiene los formularios.
        TEST_FACEBOOK_FORM: Int: Formulario el cual tiene los leads.

    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.FacebookLeads.value
        }
        cls.connection = Connection.objects.create(**_dict)

        token = os.environ.get('TEST_FACEBOOK_TOKEN')

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'token': token,
        }
        cls.facebook_connection = FacebookLeadsConnection.objects.create(**_dict2)

        action = Action.objects.get(connector_id=ConnectorEnum.FacebookLeads.value, action_type='source',
                                    name='get leads', is_active=True)

        _dict3 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug = Plug.objects.create(**_dict3)

        specification1 = ActionSpecification.objects.get(action=action, name='page')
        specification2 = ActionSpecification.objects.get(action=action, name='form')

        _dict4 = {
            'plug': cls.plug,
            'action_specification': specification1,
            'value': os.environ.get('TEST_FACEBOOK_PAGE')
        }
        PlugActionSpecification.objects.create(**_dict4)

        _dict5 = {
            'plug': cls.plug,
            'action_specification': specification2,
            'value': os.environ.get('TEST_FACEBOOK_FORM')
        }
        PlugActionSpecification.objects.create(**_dict5)

        _dict6 = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict6)

        _dict7 = {
            'gear': cls.gear
        }

        cls.gear_map = GearMap.objects.create(**_dict7)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        # self.client = Client()
        self.controller = FacebookLeadsController(self.plug.connection.related_connection, self.plug)

        self.hook = {'entry':
                         [{'id': '299300463551366', 'changes':
                             [{'value': {'form_id': '270207053469727',
                                         'page_id': '299300463551366',
                                         'created_time': 1505494516,
                                         'leadgen_id': '270800420077057'},
                               'field': 'leadgen'
                               }], 'time': 1505494516
                           }],
                     'object': 'page'}
        self.lead = {
            'value': {'page_id': '299300463551366', 'leadgen_id': '270800420077057', 'created_time': 1505494516,
                      'form_id': '270207053469727'}, 'field': 'leadgen'}

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.controller._connection_object, FacebookLeadsConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.FacebookLeads)
        self.assertIsInstance(self.controller._client, FacebookClient)

    def test_get_account(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller.get_account()
        self.assertIsInstance(result, dict)

    def test_get_pages(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller.get_pages()
        self.assertIsInstance(result, dict)

    def test_do_webhook_process(self):
        """Comprueba que la llamada al metodo devuelva un HTTP Response con un Status Code específico y que
        como resultado del proceso haya data guardada en StoredData.

        """
        result = self.controller.do_webhook_process(self.hook, POST=True)
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)

    def test_download_to_stored_data(self):
        """Comprueba que la llamada al metodo devuelva un diccionario y la existencia de los atributos necesarios y
        su respectivo tipo de dato almacenado como valor.

        """
        result = self.controller.download_to_stored_data(self.plug.connection.related_connection, self.plug,
                                                         lead=self.lead)
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
        result = self.controller.download_source_data(self.plug.connection.related_connection, self.plug,
                                                      lead=self.lead)

        qs = StoredData.objects.order_by('object_id').values_list('object_id', flat=True).distinct()
        for lead in qs:
            l = DownloadHistory.objects.first()
            count = DownloadHistory.objects.filter(identifier={'name': 'leadgen_id', 'value': lead}).count()
            self.assertGreater(count, 0)
