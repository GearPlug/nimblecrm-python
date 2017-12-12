import os
import re
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.email_marketing import MandrillController
from apps.gp.models import Connection, MandrillConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Gear, GearMap, GearMapData, MySQLConnection
from apps.history.models import DownloadHistory, SendHistory
import mandrill


class MandrillControllerTestCases(TestCase):
    """
        TEST_MANDRILL_API_KEY : String: Api key

        TEST_MANDRILL_SOURCE_MYSQL_HOST: String: Host del servidor..
        TEST_MANDRILL_SOURCE_MYSQL_DATABASE String: Nombre de la base de datos.
        TEST_MANDRILL_SOURCE_MYSQL_TABLE: String: Nombre de la tabla.
        TEST_MANDRILL_SOURCE_MYSQL_PORT: String: Nùmero de puerto.
        TEST_MANDRILL_SOURCE_MYSQL_CONNECTION_USER: String: Usuario.
        TEST_MANDRILL_SOURCE_MYSQL_CONNECTION_PASSWORD: String: Contraseña.

    """
    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.Mandrill.value
        }
        cls.source_connection = Connection.objects.create(**connection)
        cls.target_connection = Connection.objects.create(**connection)

        _source_connection = {
            'connection': cls.source_connection,
            'name': 'ConnectionTest Source',
            'host': os.environ.get('TEST_MANDRILL_SOURCE_MYSQL_HOST'),
            'database': os.environ.get('TEST_MANDRILL_SOURCE_MYSQL_DATABASE'),
            'table': os.environ.get('TEST_MANDRILL_SOURCE_MYSQL_TABLE'),
            'port': os.environ.get('TEST_MANDRILL_SOURCE_MYSQL_PORT'),
            'connection_user': os.environ.get('TEST_MANDRILL_SOURCE_MYSQL_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_MANDRILL_SOURCE_MYSQL_CONNECTION_PASSWORD')
        }

        cls.mysql_source_connection = MySQLConnection.objects.create(**_source_connection)

        _target_connection = {
            "connection": cls.target_connection,
            "name": "ConnectionTest Target",
            "api_key": os.environ.get("TEST_MANDRILL_API_KEY"),
        }
        cls.mandrill_target_connection = MandrillConnection.objects.create(**_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.MySQL.value, action_type='source', name='get row',
                                           is_active=True)

        target_action = Action.objects.get(connector_id=ConnectorEnum.Mandrill.value, action_type="target",
                                           name="send mail", is_active=True)

        _mysql_source_plug = {
            'name': 'PlugTest Source',
            'connection': cls.source_connection,
            'action': source_action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }

        cls.source_plug = Plug.objects.create(**_mysql_source_plug)

        _mandrill_target_plug = {
            "name": "PlugTest Target",
            "connection": cls.target_connection,
            "action": target_action,
            "plug_type": "target",
            "user": cls.user,
            "is_active": True
        }
        cls.target_plug = Plug.objects.create(**_mandrill_target_plug)

        gear = {
            "name": "Gear 1",
            "user": cls.user,
            "source": cls.source_plug,
            "target": cls.target_plug,
            "is_active": True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self.target_controller = MandrillController(self.target_plug.connection.related_connection,
                                                    self.target_plug)

    def _get_data(self):
        return {'view_content_link': 'False', 'auto_html': 'False', 'merge': 'False', 'preserve_recipients': 'False',
                'from_email': 'grplugtest2@gmail.com', 'url_strip_qs': 'False', 'to_email': 'grplugtest1@gmail.com',
                'inline_css': 'False', 'bcc_address': 'grplugtest2@gmail.com', 'subject': 'mensaje9',
                'track_opens': 'False', 'auto_text': 'False', 'important': 'False', 'text': '9 mensaje',
                'track_clicks': 'False'}

    def _get_fields(self):
        _dict = [
            # {
            #     'name': 'attachments',
            #     'required': False,
            #     'type': 'file'
            # },
            {
                'name': 'auto_html',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'auto_text',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'bcc_address',
                'required': False,
                'type': 'text'
            }, {
                'name': 'from_email',
                'required': False,
                'type': 'text'
            }, {
                'name': 'from_name',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'global_merge_vars',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'google_analytics_campaign',
                'required': False,
                'type': 'text'
            },
            {
                'name': 'google_analytics_domains',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'headers',
            #     'required': False,
            #     'type': 'struct'
            # },
            {
                'name': 'html',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'images',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'important',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'inline_css',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'merge',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'merge_language',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'merge_vars',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'metadata',
                'required': False,
                'type': 'array'
            }, {
                'name': 'preserve_recipients',
                'required': False,
                'type': 'bool'
            },
            # {
            #     'name': 'recipient_metadata',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'return_path_domain',
                'required': False,
                'type': 'text'
            }, {
                'name': 'signing_domain',
                'required': False,
                'type': 'text'
            }, {
                'name': 'subaccount',
                'required': False,
                'type': 'text'
            }, {
                'name': 'subject',
                'required': False,
                'type': 'text'
            }, {
                'name': 'tags',
                'required': False,
                'type': 'array'
            }, {
                'name': 'text',
                'required': False,
                'type': 'text'
            },
            # To: originalmente una lista de diccionarios
            {
                'name': 'to_email',
                'required': True,
                'type': 'text'
            },
            {
                'name': 'track_clicks',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'track_opens',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'tracking_domain',
                'required': False,
                'type': 'text'
            }, {
                'name': 'url_strip_qs',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'view_content_link',
                'required': False,
                'type': 'bool'
            },
        ]
        return _dict

    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        self.assertIsInstance(self.target_controller._connection_object, MandrillConnection)
        self.assertIsInstance(self.target_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._client, mandrill.Mandrill)

    def test_test_connection(self):
        """
        Comprueba que la conexión sea valida
        """
        target_result = self.target_controller.test_connection()
        self.assertTrue(target_result)

    def test_get_target_fields(self):
        """Verifica los fields de un contacto"""
        result = self.target_controller.get_target_fields()
        self.assertEqual(result, self._get_fields())

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.target_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_send_stored_data(self):
        _data = self._get_data()
        data_list = [OrderedDict(_data)]
        result = self.target_controller.send_stored_data(data_list)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)
        self.assertIn('data', result[-1])
        self.assertIn('response', result[-1])
        self.assertIn('sent', result[-1])
        self.assertIn('identifier', result[-1])
        self.assertIsInstance(result[-1]['data'], dict)
        self.assertIsInstance(result[-1]['response'], list)
        self.assertIsInstance(result[-1]['sent'], bool)
        self.assertEqual(result[-1]['data'], dict(data_list[0]))

    def test_send_target_data(self):
        _source = [{'data': {'subject': 'mensaje 11', 'message': '11 mensaje', 'id': '11',
                             'sender': 'grplugtest2@gmail.com', 'email': 'grplugtest1@gmail.com'}, 'id': '11'}]
        _target_fields = {'view_content_link': 'False', 'auto_html': 'False', 'metadata': '', 'merge': 'False',
                          'html': '', 'from_name': '', 'subaccount': '', 'preserve_recipients': 'False',
                          'from_email': '%%sender%%', 'url_strip_qs': 'False', 'google_analytics_campaign': '',
                          'to_email': '%%email%%', 'inline_css': 'False', 'google_analytics_domains': '', 'tags': '',
                          'bcc_address': '%%sender%%', 'subject': '%%subject%%', 'track_opens': 'False',
                          'auto_text': 'False', 'important': 'False', 'text': '%%message%%', 'signing_domain': '',
                          'merge_language': '', 'tracking_domain': '', 'track_clicks': 'False',
                          'return_path_domain': ''}
        _target = OrderedDict(_target_fields)
        result = self.target_controller.send_target_data(source_data=_source, target_fields=_target)
        count_history = SendHistory.objects.all().count()
        self.assertNotEqual(count_history, 0)

    def test_send_email(self):
        _data = OrderedDict(self._get_data())
        result = self.target_controller.send_email(_data)
        self.assertIsInstance(result, list)
        self.assertIn('_id', result[0])

    def test_get_meta(self):
        result = self.target_controller.get_meta()
        self.assertEqual(result, self._get_fields())
