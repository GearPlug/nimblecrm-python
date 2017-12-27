import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, SMTPConnection, Plug, Action, \
    ActionSpecification, PlugActionSpecification, Gear, StoredData
from apps.history.models import DownloadHistory
from apps.gp.controllers.email import SMTPController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class SlackControllerTestCases(TestCase):
    """
    TEST_SLACK_TOKEN : String: Token autorizado
    TEST_SLACK_CHANNEL : String: Canal de pruebas acciones de source o target
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer',
                                       email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.SMTP.value
        }
        cls.connection = Connection.objects.create(**_dict_connection)

        _dict_smtp_connection = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'host': os.environ.get('TEST_HOST'),
            'port': os.environ.get('TEST_PORT'),
            'connection_user': os.environ.get('TEST_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_CONNECTION_PASSWORD')
        }
        cls.smtp_connection = SMTPConnection.objects.create(**_dict_smtp_connection)

        action = Action.objects.get(connector_id=ConnectorEnum.SMTP.value,
                                    action_type='target',
                                    name='send email',
                                    is_active=True)

        _dict_action = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug = Plug.objects.create(**_dict_action)

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)

    def setUp(self):
        self.controller = SMTPController(
            self.plug.connection.related_connection, self.plug)

        self.hook = {'event_time': 1505486997, 'authed_users': ['U73RCAVE0'],
                     'event': {'type': 'message', 'ts': '1505486997.000346',
                               'text': 'Hola', 'channel': 'C73MGHMAP',
                               'event_ts': '1505486997.000346',
                               'user': 'U73RCAVE0'}, 'api_app_id': 'A734RF1K2',
                     'token': 'ieOfWCJiRhYHI4uuLODW93JL',
                     'team_id': 'T73TSKJ0M', 'event_id': 'Ev73RY51T6',
                     'type': 'event_callback'}

    def _get_fields(self):
        return [{'name': 'message'}]

    def test_controller(self):
        self.assertIsInstance(self.controller._connection_object, SMTPConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        self.assertIsNotNone(self.controller.client)

    def _get_fields(self):
        return [{'name': 'recipient', 'type': 'varchar', 'required': True},
                {'name': 'subject', 'type': 'varchar', 'required': False},
                {'name': 'message', 'type': 'varchar', 'required': True}, ]

    def test_connection(self):
        """
        """
        result = self.controller.test_connection()
        self.assertTrue(result)

    def test_get_mapping_fields(self):
        """
        Verifica que el método retorne una instancia de MappingFields
        """
        result = self.controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_target_fields(self):
        result = self.controller.get_target_fields()
        self.assertEqual(result, self._get_fields())

    def test_send_stored_data(self):
        """simula un dato de entrada y comprueba que retrorne una lista de acuerdo a los parámetros establecidos"""
        data_list=[OrderedDict({"message": "test message",
                                "recipient":"nrincon@grplug.com",
                                "subject": "Test subject"})]
        result = self.controller.send_stored_data(data_list)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)
        self.assertIn('data', result[-1])
        self.assertIn('response', result[-1])
        self.assertIn('sent', result[-1])
        self.assertIn('identifier', result[-1])
        self.assertIsInstance(result[-1]['data'], dict)
        self.assertIsInstance(result[-1]['response'], str)
        self.assertIsInstance(result[-1]['sent'], bool)
        self.assertEqual(result[-1]['data'], dict(data_list[0]))
