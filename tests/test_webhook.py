import ast
import json
import os
import requests
from django.conf import settings
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.shortcuts import HttpResponse
from apps.gp.models import Connection, WebhookConnection, Plug, Action, ActionSpecification, PlugActionSpecification, \
    Gear, GearMap, StoredData, GearMapData, Webhook, MySQLConnection
from apps.history.models import DownloadHistory, SendHistory
from apps.gp.controllers.database import MySQLController
from apps.gp.controllers.various import WebhookController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class WebhookControllerTestCases(TestCase):
    """Casos de prueba del controlador Webhook.

        Variables de entorno:
            TEST_MYSQL_TARGET_HOST: String: Host del servidor..
            TEST_MYSQL_TARGET_DATABASE String: Nombre de la base de datos.
            TEST_MYSQL_TARGET_TABLE: String: Nombre de la tabla.
            TEST_MYSQL_TARGET_PORT: String: Nùmero de puerto.
            TEST_MYSQL_TARGET_CONNECTION_USER: String: Usuario.
            TEST_MYSQL_TARGET_CONNECTION_PASSWORD: String: Contraseña.

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
            'connector_id': ConnectorEnum.Webhook.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        webhook_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source'
        }
        cls.webhook_connection1 = WebhookConnection.objects.create(**webhook_connection1)

        cls.connection_target = Connection.objects.create(**connection)

        mysql_connection1 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'host': os.environ.get('TEST_MYSQL_TARGET_HOST'),
            'database': os.environ.get('TEST_MYSQL_TARGET_DATABASE'),
            'table': os.environ.get('TEST_MYSQL_TARGET_TABLE'),
            'port': os.environ.get('TEST_MYSQL_TARGET_PORT'),
            'connection_user': os.environ.get('TEST_MYSQL_TARGET_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_MYSQL_TARGET_CONNECTION_PASSWORD')
        }
        cls.mysql_connection1 = MySQLConnection.objects.create(**mysql_connection1)

        action_source = Action.objects.get(connector_id=ConnectorEnum.Webhook.value, action_type='source',
                                           name='post received', is_active=True)

        webhook_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_source = Plug.objects.create(**webhook_plug_source)

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
        # self.client = Client()
        self.source_controller = WebhookController(self.plug_source.connection.related_connection, self.plug_source)

        self.hook = {'nombre': 'miguel', 'apellido': 'ferrer'}

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.source_controller._connection_object, WebhookConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)

    def test_do_webhook_process(self):
        """Comprueba que la llamada al metodo devuelva un HTTP Response con un Status Code específico y que
        como resultado del proceso haya data guardada en StoredData.

        """
        _dict = {
            'name': 'webhook',
            'plug': self.plug_source,
            'url': settings.WEBHOOK_HOST,
            'expiration': '',
            'generated_id': '1',
            'is_active': True
        }
        webhook = Webhook.objects.create(**_dict)
        result = self.source_controller.do_webhook_process(self.hook, POST=True, webhook_id=webhook.id)
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)

    def test_download_to_stored_data(self):
        """Comprueba que la llamada al metodo devuelva un diccionario y la existencia de los atributos necesarios y
        su respectivo tipo de dato almacenado como valor.

        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, body=self.hook)

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
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source, body=self.hook)

        qs = StoredData.objects.order_by('object_id').values_list('object_id', flat=True).distinct()
        for lead in qs:
            count = DownloadHistory.objects.filter(identifier={'name': 'timestamp', 'value': lead}).count()
            self.assertGreater(count, 0)
