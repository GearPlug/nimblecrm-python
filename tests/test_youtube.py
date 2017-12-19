import ast
import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, MySQLConnection, YouTubeConnection, Plug, Action, ActionSpecification, \
    PlugActionSpecification, Gear, StoredData, Webhook
from apps.gp.controllers.social import YouTubeController
from apps.gp.controllers.database import MySQLController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.history.models import DownloadHistory


class YoutubeControllerTestCases(TestCase):
    """
    TEST_YOUTUBE_TOKEN: String: Usuario
    TEST_YOUTUBE_CHANNEL: String: Canal

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
        cls.user = User.objects.create(username='lrubiano@grplug.com', email='lrubiano@grplug.com',
                                       password='Prueba#2017')
        # SOURCE CONNECTION
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.YouTube.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        youtube_connection = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest',
            'credentials_json': ast.literal_eval(os.environ.get('TEST_YOUTUBE_TOKEN')),
        }
        cls.youtube_connection = YouTubeConnection.objects.create(**youtube_connection)
        #####

        # TARGET CONNECTION
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.MySQL.value
        }
        cls.connection_target = Connection.objects.create(**connection)

        mysql_connection = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'host': os.environ.get('TEST_MYSQL_TARGET_HOST'),
            'database': os.environ.get('TEST_MYSQL_TARGET_DATABASE'),
            'table': os.environ.get('TEST_MYSQL_TARGET_TABLE'),
            'port': os.environ.get('TEST_MYSQL_TARGET_PORT'),
            'connection_user': os.environ.get('TEST_MYSQL_TARGET_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_MYSQL_TARGET_CONNECTION_PASSWORD')
        }
        cls.mysql_connection = MySQLConnection.objects.create(**mysql_connection)
        #####

        # PLUG SOURCE
        source_action = Action.objects.get(connector_id=ConnectorEnum.YouTube.value, action_type='source',
                                           name='push notification', is_active=True)

        youtube_plug_source = {
            'name': 'PlugTest',
            'connection': cls.connection_source,
            'action': source_action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_source = Plug.objects.create(**youtube_plug_source)
        #####

        # PLUG TARGET
        action_target = Action.objects.get(connector_id=ConnectorEnum.MySQL.value, action_type='target',
                                           name='create row', is_active=True)

        mysql_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**mysql_plug_target)
        #####

        # ACTION SPECIFICATIONS SOURCE
        cls.source_specification = ActionSpecification.objects.get(action=source_action, name='channel')

        _dict_source_specification = {
            'plug': cls.plug_source,
            'action_specification': cls.source_specification,
            'value': os.environ.get('TEST_YOUTUBE_CHANNEL')
        }
        PlugActionSpecification.objects.create(**_dict_source_specification)
        #####

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.
        """
        self.source_controller = YouTubeController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = MySQLController(self.plug_target.connection.related_connection, self.plug_target)

        self.hook = '<?xml version="1.0" encoding="UTF-8"?><feed xmlns:yt="http://www.youtube.com/xml/schemas/2015" xmlns="http://www.w3.org/2005/Atom"><link rel="hub" href="https://pubsubhubbub.appspot.com"/><link rel="self" href="https://www.youtube.com/xml/feeds/videos.xml?channel_id=UC7d1wZsLdg9pcU5JxaHhNJw"/><title>YouTube video feed</title><updated>2017-12-15T14:28:16.109921364+00:00</updated><entry><id>yt:video:KtMyGttbyq0</id><yt:videoId>KtMyGttbyq0</yt:videoId><yt:channelId>UC7d1wZsLdg9pcU5JxaHhNJw</yt:channelId><title>vid</title><link rel="alternate" href="https://www.youtube.com/watch?v=KtMyGttbyq0"/><author><name>Miguel Ferrer</name><uri>https://www.youtube.com/channel/UC7d1wZsLdg9pcU5JxaHhNJw</uri></author><published>2017-12-14T15:47:14+00:00</published><updated>2017-12-15T14:28:16.109921364+00:00</updated></entry></feed>'

        self.video = {'pageInfo': {'totalResults': 1, 'resultsPerPage': 1}, 'kind': 'youtube#videoListResponse',
                      'items': [{'snippet': {'categoryId': '22', 'channelTitle': 'Miguel Ferrer', 'thumbnails': {
                          'high': {'url': 'https://i.ytimg.com/vi/KtMyGttbyq0/hqdefault.jpg', 'width': 480,
                                   'height': 360},
                          'standard': {'url': 'https://i.ytimg.com/vi/KtMyGttbyq0/sddefault.jpg', 'width': 640,
                                       'height': 480},
                          'maxres': {'url': 'https://i.ytimg.com/vi/KtMyGttbyq0/maxresdefault.jpg', 'width': 1280,
                                     'height': 720},
                          'medium': {'url': 'https://i.ytimg.com/vi/KtMyGttbyq0/mqdefault.jpg', 'width': 320,
                                     'height': 180},
                          'default': {'url': 'https://i.ytimg.com/vi/KtMyGttbyq0/default.jpg', 'width': 120,
                                      'height': 90}}, 'channelId': 'UC7d1wZsLdg9pcU5JxaHhNJw',
                                             'publishedAt': '2017-12-14T15:47:14.000Z', 'title': 'vid',
                                             'description': '13', 'localized': {'title': 'vid', 'description': '13'},
                                             'liveBroadcastContent': 'none'}, 'kind': 'youtube#video',
                                 'id': 'KtMyGttbyq0',
                                 'etag': '"S8kisgyDEblalhHF9ooXPiFFrkc/ZBHAGLita4_lFtK_eqvzOQ5HSHA"'}],
                      'etag': '"S8kisgyDEblalhHF9ooXPiFFrkc/2vxeeBelqsj6eTXx5nJA5ubKSJs"'}

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.
        """
        self.assertIsInstance(self.source_controller._connection_object, YouTubeConnection)
        self.assertIsInstance(self.target_controller._connection_object, MySQLConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)
        self.assertNotEqual(self.source_controller._client, None)
        self.assertNotEqual(self.target_controller._connection, None)

    def test_test_connection(self):
        """
        Verifica que la conexión este establecida
        """
        result = self.source_controller.test_connection()
        self.assertNotEqual(result, None)

        result = self.target_controller.test_connection()
        self.assertNotEqual(result, None)

    def test_do_webhook_process(self):
        """Simula un dato de entrada (self.hook), se crea un webhook y se verifica que retorne
        un status code =200, al final se borra el webhook"""
        self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        result = self.source_controller.do_webhook_process(body=self.hook, webhook_id=webhook.id)
        self.assertEqual(result.status_code, 200)
        result = self.source_controller.delete_webhook(webhook)
        self.assertEqual(result.status_code, 202)

    def test_download_source_data(self):
        """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
        count_data = len(self.video['items'][0]['snippet'])
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source, video=self.video)
        count_store = StoredData.objects.filter(connection=self.connection_source, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        self.assertEqual(count_store, count_data)
        self.assertEqual(history.identifier, str({'name': 'id', 'value': self.video['items'][0]['id']}))

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
                                                                self.plug_source, video=self.video)
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

    def test_get_mapping_fields(self):
        """Comprueba que el resultado sea una instancia de Mapfields
        """
        result = self.source_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertTrue(result)
        self.assertIsInstance(result[0], MapField)

    def test_get_target_fields(self):
        """
        Comprueba que traiga los fields esperados
        """
        result = self.target_controller.get_target_fields()
        self.assertEqual(result, self.target_controller.get_target_fields())

    def test_get_action_specification_options(self):
        """
        Testea que traiga los proyectos creados en la aplicación, funciona mediante la variable
        TEST_JIRA_PROJECT, el cual debe ser un ID de un proyecto real creado en la aplicación
        """
        action_specification_id = self.source_specification.id
        result = self.source_controller.get_action_specification_options(action_specification_id)
        self.assertIsInstance(result, tuple)
        self.assertTrue(result)

    def test_get_channel_list(self):
        """
        Testea que traiga los proyectos creados en la aplicación, funciona mediante la variable
        TEST_JIRA_PROJECT, el cual debe ser un ID de un proyecto real creado en la aplicación
        """
        result = self.source_controller.get_channel_list()
        self.assertIsInstance(result, list)
        self.assertTrue(result)

    def test_get_video_categories(self):
        """
        Testea que traiga los proyectos creados en la aplicación, funciona mediante la variable
        TEST_JIRA_PROJECT, el cual debe ser un ID de un proyecto real creado en la aplicación
        """
        result = self.source_controller.get_video_categories()
        self.assertIsInstance(result, list)
        self.assertTrue(result)
