import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, SlackConnection, Plug, Action, \
    ActionSpecification, PlugActionSpecification, Gear, StoredData
from apps.history.models import DownloadHistory
from apps.gp.controllers.im import SlackController
from slacker import Slacker
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
        _dict_connection_source = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Slack.value
        }
        cls.connection_source = Connection.objects.create(**_dict_connection_source)

        _dict_connection_target = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Slack.value
        }
        cls.connection_target = Connection.objects.create(**_dict_connection_target)

        token = os.environ.get('TEST_SLACK_TOKEN')

        _dict_slack_connection_source = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest',
            'token': token,
        }
        cls.slack_connection_source = SlackConnection.objects.create(**_dict_slack_connection_source)
        _dict_slack_connection_target = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest',
            'token': token,
        }
        cls.slack_connection_target = SlackConnection.objects.create(**_dict_slack_connection_target)

        action_source = Action.objects.get(connector_id=ConnectorEnum.Slack.value,
                                    action_type='source',
                                    name='new message posted to a chanel',
                                    is_active=True)

        action_target = Action.objects.get(connector_id=ConnectorEnum.Slack.value,
                                           action_type='target',
                                           name='post message to a channel',
                                           is_active=True)

        _dict_action_source = {
            'name': 'PlugTest',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**_dict_action_source)

        _dict_action_target = {
            'name': 'PlugTest',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**_dict_action_target)

        cls.specification_source = ActionSpecification.objects.get(action=action_source,
                                                         name='channel')

        cls.specification_target = ActionSpecification.objects.get(action=action_target,
                                                               name='channel')

        _dict_specification_source = {
            'plug': cls.plug_source,
            'action_specification': cls.specification_source,
            'value': os.environ.get('TEST_SLACK_CHANNEL')
        }
        PlugActionSpecification.objects.create(**_dict_specification_source)

        _dict_specification_target = {
            'plug': cls.plug_target,
            'action_specification': cls.specification_target,
            'value': os.environ.get('TEST_SLACK_CHANNEL')
        }
        PlugActionSpecification.objects.create(**_dict_specification_target)

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)

    def setUp(self):
        # self.client = Client()
        self.controller_source = SlackController(
            self.plug_source.connection.related_connection, self.plug_source)

        self.controller_target = SlackController(
            self.plug_target.connection.related_connection, self.plug_target)

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
        self.assertIsInstance(self.controller_source._connection_object, SlackConnection)
        self.assertIsInstance(self.controller_target._connection_object, SlackConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertIsInstance(self.controller_target._plug, Plug)
        self.assertIsInstance(self.controller_source._slacker, Slacker)
        self.assertIsInstance(self.controller_target._slacker, Slacker)
        self.assertEqual(self.controller_source._token, os.environ.get('TEST_SLACK_TOKEN'))
        self.assertEqual(self.controller_target._token, os.environ.get('TEST_SLACK_TOKEN'))

    def test_get_channel_list(self):
        """
        Verifica que traiga la lista de canales asociados a la cuenta
        """
        result = self.controller_source.get_channel_list()
        self.assertIsInstance(result, tuple)

    def test_get_mapping_fields(self):
        """
        Verifica que el método retorne una instancia de MappingFields
        """
        result = self.controller_target.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_post_message_to_target(self):
        """Verifica que se escriba un mensaje en un canal"""
        result = self.controller_target.post_message_to_target('Hashtag #nerioOnIce', os.environ.get('TEST_SLACK_CHANNEL'))
        self.assertEqual(result.__dict__['body']['channel'], os.environ.get('TEST_SLACK_CHANNEL'))

    def test_post_message_to_channel(self):
        """Verifica que se escriba un mensaje en un canal"""
        result = self.controller_target.post_message_to_channel('Hashtag #nerioOnIce', os.environ.get('TEST_SLACK_CHANNEL'))
        self.assertIsNot(result, False)

    def test_post_message_to_user(self):
        """Verifica que se escriba un mensaje a un usuario"""
        result = self.controller_target.post_message_to_channel('Hashtag #nerioOnIce', os.environ.get('TEST_SLACK_CHANNEL'))
        self.assertIsNot(result, False)

    def test_do_webhook_process(self):
        """Verifica que se escriba un mensaje en un canal"""
        self.gear.is_active = True
        result = self.controller_source.do_webhook_process(body=self.hook)
        self.assertEqual(result.status_code, 200)

    def test_get_target_fields(self):
        result = self.controller_target.get_target_fields()
        self.assertEqual(result, self._get_fields())

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.controller_target.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_action_specification_options(self):
        """Testea que retorne los action specification de manera correcta los canales de la cuenta"""
        action_specification_id = self.specification_target.id
        result = self.controller_target.get_action_specification_options(action_specification_id)
        _channel = None
        for i in result:
            if i["id"] == os.environ.get("TEST_SLACK_CHANNEL"):
                _channel = i["id"]
        self.assertIsInstance(result, tuple)
        self.assertEqual(_channel, os.environ.get("TEST_SLACK_CHANNEL"))

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.controller_source.download_to_stored_data(self.plug_source.connection.related_connection, self.plug_source,
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
        count_start = StoredData.objects.filter(connection=self.connection_source, plug=self.plug_source).count()
        result = self.controller_source.download_source_data(self.plug_source.connection.related_connection, self.plug_source,
                                                             event=self.hook)
        count_end = StoredData.objects.filter(connection=self.connection_source, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        self.assertEqual(count_end, count_start + 1)
        data = str({self.hook['event']['type']:self.hook['event']['text']})
        self.assertEqual(history.raw, data.replace("'", '"'))
        self.assertEqual(history.identifier, str({'name':'event_id', 'value': self.hook['event_id']}))
        self.assertTrue(result)

    def test_send_stored_data(self):
        """simula un dato de entrada y comprueba que retrorne una lista de acuerdo a los parámetros establecidos"""
        data_list=[OrderedDict({"message": "Hashtag #nerioOnIce"})]
        result = self.controller_target.send_stored_data(data_list)
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
