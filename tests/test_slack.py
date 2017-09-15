import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, SlackConnection, Plug, Action, \
    ActionSpecification, PlugActionSpecification, Gear, StoredData
from apps.gp.controllers.im import SlackController
from slacker import Slacker
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField


class SlackControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer',
                                       email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Slack.value
        }
        cls.connection = Connection.objects.create(**_dict)

        token = os.environ.get('token')

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'token': token,
        }
        cls.slack_connection = SlackConnection.objects.create(**_dict2)

        action = Action.objects.get(connector_id=ConnectorEnum.Slack.value,
                                    action_type='source',
                                    name='new message posted to a chanel',
                                    is_active=True)

        _dict3 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug = Plug.objects.create(**_dict3)

        specification1 = ActionSpecification.objects.get(action=action,
                                                         name='channel')

        _dict4 = {
            'plug': cls.plug,
            'action_specification': specification1,
            'value': 'C73MGHMAP'
        }
        PlugActionSpecification.objects.create(**_dict4)

        _dict5 = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict5)

    def setUp(self):
        # self.client = Client()
        self.controller = SlackController(
            self.plug.connection.related_connection, self.plug)

        self.hook = {'event_time': 1505486997, 'authed_users': ['U73RCAVE0'],
                     'event': {'type': 'message', 'ts': '1505486997.000346',
                               'text': 'Hola', 'channel': 'C73MGHMAP',
                               'event_ts': '1505486997.000346',
                               'user': 'U73RCAVE0'}, 'api_app_id': 'A734RF1K2',
                     'token': 'ieOfWCJiRhYHI4uuLODW93JL',
                     'team_id': 'T73TSKJ0M', 'event_id': 'Ev73RY51T6',
                     'type': 'event_callback'}

    def test_controller(self):
        self.assertIsInstance(self.controller._connection_object,
                              SlackConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.Slack)
        self.assertIsInstance(self.controller._slacker, Slacker)

    def test_get_channel_list(self):
        result = self.controller.get_channel_list()
        self.assertIsInstance(result, tuple)

    def test_get_mapping_fields(self):
        result = self.controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_post_message_to_channel(self):
        result = self.controller.post_message_to_channel('Hashtag #nerioOnIce', os.environ.get('channel'))
        self.assertIsNot(result, False)

    def test_do_webhook_process(self):
        result = self.controller.do_webhook_process(self.hook)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)
