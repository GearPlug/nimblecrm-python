import os
from django.test import TestCase
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.crm import ActiveCampaignController
from apps.gp.models import Connection, ActiveCampaignConnection, Action, Plug, ActionSpecification, PlugActionSpecification


class ActiveCampaignControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod

    def setUpTestData(cls):

        cls.user = User.objects.create(username='test',
                                       email='lyrubiano5@gmail.com',
                                       password='Prueba#2017')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.ActiveCampaign.value
        }
        cls.connection = Connection.objects.create(**_dict)

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_ACTIVECAMPAIGN_TOKEN'),
        }
        cls.activecampaign_connection = ActiveCampaignConnection.objects.create(**_dict2)

        action_source = Action.objects.get(connector_id=ConnectorEnum.ActiveCampaign.value,
                                    action_type='source',
                                    name='pendiente',
                                    is_active=True)

        action_target = Action.objects.get(connector_id=ConnectorEnum.ActiveCampaign.value,
                                            action_type='target',
                                            name='pendiente',
                                            is_active=True)

        _dict3 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }

        cls.plug_source = Plug.objects.create(**_dict3)

        _dict4 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }

        cls.plug_target = Plug.objects.create(**_dict4)

        cls.specification_source = ActionSpecification.objects.get(action=action_source, name=os.environ.get('TEST_ACTIVECAMPAIGN_LIST'))
        cls.specification_target = ActionSpecification.objects.get(action=action_target, name='TEST_ACTIVECAMPAIGN_LIST')

        _dict5 = {
            'plug': cls.plug_source,
            'action_specification': cls.specification_source,
            'value': os.environ.get('TEST_ACTIVECAMPAIGN_SHEET')
        }

        cls.plug_action_specificaion_source = PlugActionSpecification.objects.create(
            **_dict5)

        _dict6 = {
            'plug': cls.plug_target,
            'action_specification': cls.specification_target,
            'value': os.environ.get('TEST_ACTIVECAMPAIGN_SHEET')
        }

        cls.plug_action_specificaion_target = PlugActionSpecification.objects.create(
            **_dict6)

        def setUp(self):
            self.controller_source = ActiveCampaignController(self.plug.connection.related_connection, self.plug_source)
            self.controller_target = ActiveCampaignController(self.plug.connection.related_connection, self.plug_target)
            self._token = os.environ.get('token')
            self._client = Client(access_token=self._token)