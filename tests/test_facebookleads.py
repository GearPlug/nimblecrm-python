from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, FacebookLeadsConnection, Plug, Action, ActionSpecification, \
    PlugActionSpecification
from apps.gp.controllers.lead import FacebookLeadsController
from facebookmarketing.client import Client as FacebookClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField


class FacebookControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.FacebookLeads.value
        }
        cls.connection = Connection.objects.create(**_dict)

        token = 'EAABpnLldYUMBAIaiqMvWD0YZAIs4w97ktgHx73tQ4M8a3cygeGWCA5MCcFq51yVPL81uEt5rS7ZAZACBnh7C0sKMj5Vr2bWlwU0ZByEUeJ2jxAAAglksJ5fuKugZBDecsDztWh9GPM13VTGtxPGA6qB2Uj3bY9QV4ZATyZCMHKQdQZDZD'

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
            'value': '299300463551366'
        }
        PlugActionSpecification.objects.create(**_dict4)

        _dict5 = {
            'plug': cls.plug,
            'action_specification': specification2,
            'value': '1838698066366754'
        }
        PlugActionSpecification.objects.create(**_dict5)

    def setUp(self):
        # self.client = Client()
        self.controller = FacebookLeadsController(self.plug.connection.related_connection, self.plug)

    def test_controller(self):
        self.assertIsInstance(self.controller._connection_object, FacebookLeadsConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.FacebookLeads)
        self.assertIsInstance(self.controller._client, FacebookClient)

    def test_get_account(self):
        result = self.controller.get_account()
        self.assertIsInstance(result, dict)

    def test_get_pages(self):
        result = self.controller.get_pages()
        self.assertIsInstance(result, dict)
