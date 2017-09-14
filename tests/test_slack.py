import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, SlackConnection, Plug, Action
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
                                    action_type='target',
                                    name='post message to a channel',
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

    def setUp(self):
        # self.client = Client()
        self.controller = SlackController(
            self.plug.connection.related_connection, self.plug)

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

    # def test_post_message_to_channel(self):
    #     result = self.controller.post_message_to_channel('Hashtag #nerioOnIce',
    #                                                      os.environ.get('channel'))
    #     self.assertIsNot(result, False)
