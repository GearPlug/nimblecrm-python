import os
import pprint
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.crm import ActiveCampaignController
from apps.gp.models import Connection, ActiveCampaignConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Webhook, \
    StoredData


class ActiveCampaignControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):

        cls.user = User.objects.create(username='test',
                                       email='lyrubiano5@gmail.com',
                                       password='Prueba#2017')
        _dict_user = {
            'user': cls.user,
            'connector_id': ConnectorEnum.ActiveCampaign.value
        }
        cls.connection = Connection.objects.create(**_dict_user)

        _dict_connection = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'host': os.environ.get('TEST_ACTIVECAMPAIGN_HOST'),
            'connection_access_key': os.environ.get('TEST_ACTIVECAMPAIGN_KEY'),
        }
        cls.activecampaign_connection = ActiveCampaignConnection.objects.create(**_dict_connection)

        action_source = Action.objects.get(connector_id=ConnectorEnum.ActiveCampaign.value,
                                           action_type='source',
                                           name='new contact',
                                           is_active=True)

        action_target = Action.objects.get(connector_id=ConnectorEnum.ActiveCampaign.value,
                                           action_type='target',
                                           name='create contact',
                                           is_active=True)

        _dict_plug_source = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }

        cls.plug_source = Plug.objects.create(**_dict_plug_source)

        _dict_plug_target = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }

        cls.plug_target = Plug.objects.create(**_dict_plug_target)

        cls.specification_source = ActionSpecification.objects.get(action=action_source, name='list')
        cls.specification_target = ActionSpecification.objects.get(action=action_target, name='list')

        _dict_plug_action_specification_source = {
            'plug': cls.plug_source,
            'action_specification': cls.specification_source,
            'value': os.environ.get('TEST_ACTIVECAMPAIGN_LIST')
        }

        cls.plug_action_specificaion_source = PlugActionSpecification.objects.create(
            **_dict_plug_action_specification_source)

        _dict_plug_action_specification_target = {
            'plug': cls.plug_target,
            'action_specification': cls.specification_target,
            'value': os.environ.get('TEST_ACTIVECAMPAIGN_LIST')
        }

        cls.plug_action_specificaion_target = PlugActionSpecification.objects.create(
            **_dict_plug_action_specification_target)

    def setUp(self):
        self.controller_source = ActiveCampaignController(self.plug_source.connection.related_connection,
                                                          self.plug_source)
        self.controller_target = ActiveCampaignController(self.plug_target.connection.related_connection,
                                                          self.plug_target)

    def _get_fields(self):
        return [{'name': 'email', 'type': 'varchar', 'required': True},
                {'name': 'first_name', 'type': 'varchar', 'required': False},
                {'name': 'last_name', 'type': 'varchar', 'required': False},
                {'name': 'phone', 'type': 'varchar', 'required': False},
                {'name': 'orgname', 'type': 'varchar', 'required': False},
                ]

    def _get_contact(self):
        return [{'initiated_by': 'admin', 'contact[id]': '14', 'contact[email]': 'contact@hotmail.com',
                 'contact[tags]': '', 'list': '0', 'contact[orgname]': '', 'orgname': '',
                 'contact[first_name]': 'contact', 'initiated_from': 'admin', 'contact[phone]': '1245',
                 'date_time': '2017-09-20T11:46:29-05:00', 'contact[last_name]': 'new',
                 'contact[ip]': '0.0.0.0', 'type': 'subscribe'}]

    def test_controller(self):
        self.assertIsInstance(self.controller_source._connection_object, ActiveCampaignConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertIsInstance(self.controller_target._plug, Plug)
        self.assertTrue(self.controller_source._host)
        self.assertTrue(self.controller_target._host)
        self.assertTrue(self.controller_source._key)
        self.assertTrue(self.controller_target._key)

    def test_get_account_info(self):
        result = self.controller_source.get_account_info()
        self.assertTrue(result)

    def test_get_lists(self):
        list = ""
        result = self.controller_source.get_lists()
        for i in result:
            if i['id'] == os.environ.get('TEST_ACTIVECAMPAIGN_LIST'):
                list = i['id']
        self.assertEqual(list, os.environ.get('TEST_ACTIVECAMPAIGN_LIST'))

    def test_get_action_specification_options(self):
        action_specification_id = self.specification_target.id
        result = self.controller_target.get_action_specification_options(action_specification_id)
        list = ""
        for i in result:
            if i['id'] == os.environ.get('TEST_ACTIVECAMPAIGN_LIST'):
                list = i['id']
        self.assertIsInstance(result, tuple)
        self.assertEqual(list, os.environ.get('TEST_ACTIVECAMPAIGN_LIST'))

    def test_get_mapping_fields(self):
        result = self.controller_target.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_target_fiels(self):
        result = self.controller_target.get_target_fields()
        self.assertEqual(result, self._get_fields())

    def test_create_user(self):
        data = {"email": os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')}
        result_create = self.controller_target.create_user(data)
        id = result_create['subscriber_id']
        result_delete = self.controller_target.delete_contact(id)
        self.assertEqual('Contact added', result_create['result_message'])
        self.assertEqual('Contact deleted', result_delete['result_message'])

    def test_create_webhook(self):
        count_start = Webhook.objects.filter(plug=self.plug_source).count()
        result = self.controller_source.create_webhook()
        count_end = Webhook.objects.filter(plug=self.plug_source).count()
        webhook = Webhook.objects.last()
        deleted = self.controller_source.delete_webhooks(webhook.generated_id)
        self.assertEqual(count_start + 1, count_end)
        self.assertTrue(result)
        self.assertEqual('Webhook deleted', deleted['result_message'])

    def test_download_to_stored_data(self):
        count_start = StoredData.objects.filter(connection=self.connection, plug=self.plug_source).count()
        data = self._get_contact()
        data[0]["email"] = os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')
        count_data = 0
        for i in data[0]:
            count_data = count_data + 1
        result = self.controller_source.download_source_data(data=data)
        count_end = StoredData.objects.filter(connection=self.connection, plug=self.plug_source).count()
        store = StoredData.objects.filter(connection=self.connection, plug=self.plug_source)
        value = None
        for i in store:
            if i.value == os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL'):
                value = i.value
        self.assertEqual(value, os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL'))
        self.assertEqual(count_end, count_start + count_data)
        self.assertTrue(result)

    def test_send_stored_data(self):
        target_fields = OrderedDict([(f['name'], "%%{0}%%".format(f['name'])) for f in self._get_fields()])
        data = {'email': os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')}
        source_data = [{'id': 1, 'data': data}]
        result = self.controller_target.send_stored_data(source_data, target_fields, is_first=True)
        contact = self.controller_target.view_contact(result[0])
        delete = self.controller_target.delete_contact(result[0])
        self.assertEqual(contact['email'], os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL'))
        self.assertEqual(delete['result_code'], 1)
        self.assertIsInstance(result, list)
