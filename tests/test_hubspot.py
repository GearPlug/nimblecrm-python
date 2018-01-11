import os
import re
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.crm import HubSpotController
from apps.gp.models import Connection, HubSpotConnection, Action, Plug, StoredData, Gear, GearMap, GearMapData
from apps.history.models import DownloadHistory, SendHistory
from hubspot.client import Client as HubSpotClient

class HubSpotControllerTestCases(TestCase):
    """
        TEST_HUBSPOT_TOKEN : String: Token Autorizado en la aplicación
        TEST_HUBSPOT_REFRESH_TOKEN : String: Refresh token para hubspot
        TEST_HUBSPOT_EMAIL : String: Email, No debe existir un contacto con este email en el CRM
    """
    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.HubSpot.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        _connection_source = {
            "connection": cls.connection_source,
            "name": "ConnectionTest Source",
            "token": os.environ.get("TEST_HUBSPOT_TOKEN"),
            "refresh_token": os.environ.get("TEST_HUBSPOT_REFRESH_TOKEN")
        }
        cls.hubspot_connection_source = HubSpotConnection.objects.create(**_connection_source)

        cls.connection_target = Connection.objects.create(**connection)

        _connection_target = {
            "connection": cls.connection_target,
            "name": "ConnectionTest Target",
            "token": os.environ.get("TEST_HUBSPOT_TOKEN"),
            "refresh_token": os.environ.get("TEST_HUBSPOT_REFRESH_TOKEN")
        }
        cls.hubspot_connection_target = HubSpotConnection.objects.create(**_connection_target)

        _list_source_actions = ['new contact', 'new company', 'new deal']

        cls._list_source_plugs = []

        for action in _list_source_actions:
            action_source = Action.objects.get(connector_id=ConnectorEnum.HubSpot.value, action_type="source",
                                               name=action, is_active=True)
            hubspot_plug_source = {
                "name": "PlugTest Source",
                "connection": cls.connection_source,
                "action": action_source,
                "plug_type": "source",
                "user": cls.user,
                "is_active": True
            }
            _source_plug = Plug.objects.create(**hubspot_plug_source)
            cls._list_source_plugs.append(
                {'action': action, 'plug': _source_plug})

        _list_target_actions = ['create contact', 'create company', 'create deal']
        cls._list_target_plugs = []

        for action in _list_target_actions:
            action_target = Action.objects.get(connector_id=ConnectorEnum.HubSpot.value, action_type="target",
                                               name=action, is_active=True)
            hubspot_plug_target = {
                "name": "PlugTest Target",
                "connection": cls.connection_target,
                "action": action_target,
                "plug_type": "target",
                "user": cls.user,
                "is_active": True
            }
            _plug_target = Plug.objects.create(**hubspot_plug_target)
            cls._list_target_plugs.append(
                {'action': action, 'plug': _plug_target})

        for _plug in cls._list_source_plugs:
            _dict_gear = {
                "name": "Gear 1",
                "user": cls.user,
                "source": _plug['plug'],
                "target": cls._list_target_plugs[0]['plug'],
                "is_active": True
            }
            _gear = Gear.objects.create(**_dict_gear)
            _gear_map = GearMap.objects.create(gear=_gear)
            _plug['gear'] = _gear
            _plug['gear_map'] = _gear_map

        for _plug in cls._list_target_plugs:
            _dict_gear = {
                "name": "Gear 1",
                "user": cls.user,
                "source": cls._list_source_plugs[0]['plug'],
                "target": _plug['plug'],
                "is_active": True
            }
            _gear = Gear.objects.create(**_dict_gear)
            _gear_map = GearMap.objects.create(gear=_gear)
            _plug['gear'] = _gear
            _plug['gear_map'] = _gear_map

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self._list_source_controllers = []
        self._list_target_controllers = []
        for _plug in self._list_source_plugs:
            source_controller = HubSpotController(_plug['plug'].connection.related_connection, _plug['plug'])
            self._list_source_controllers.append({'action': _plug['action'], 'controller': source_controller,
                                                  'plug': _plug['plug'], 'gear': _plug['gear'], 'gear_map': _plug['gear_map']})
        for _plug in self._list_target_plugs:
            target_controller = HubSpotController(_plug['plug'].connection.related_connection, _plug['plug'])
            self._list_target_controllers.append({'action': _plug['action'], 'controller': target_controller,
                                                  'plug': _plug['plug']})

    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        _total_controllers = self._list_source_controllers + self._list_target_controllers
        for _controller in _total_controllers:
            self.assertIsInstance(_controller['controller']._connection_object, HubSpotConnection)
            self.assertIsInstance(_controller['controller']._plug, Plug)
            self.assertIsInstance(_controller['controller']._client, HubSpotClient)

    def test_test_connection(self):
        _total_controllers = self._list_source_controllers + self._list_target_controllers
        for _controller in _total_controllers:
            result = _controller['controller'].test_connection()
            self.assertTrue(result)

    def test_get_data(self):
        """
        Antes de realizar este test, verificar la existencia de contactos en instacia de HubSpot.
        :return:
        """
        for _controller in self._list_source_controllers:
            result = _controller['controller'].get_data(_controller['action'])
            self.assertIsInstance(result, list)
            self.assertIsInstance(result[0], dict)

    def test_get_id(self):
        result_compare = {'new contact': 'vid', 'new company' : 'companyId', 'new deal': 'dealId'}
        for _controller in self._list_source_controllers:
            result = _controller['controller'].get_id(_controller['action'])
            self.assertEqual(result_compare[_controller['action']], result)

    def test_get_item(self):
        for _controller in self._list_source_controllers:
            if (_controller['action'] == 'new contact'):
                result_create = _controller['controller']._client.contacts.create_contact({'email': os.environ.get('TEST_HUBSPOT_EMAIL')}).json()
                result = _controller['controller'].get_item(_controller['action'], result_create['vid'])
                self.assertEqual(result_create['vid'], result['vid'])
                _controller['controller']._client.contacts.delete_contact(result_create['vid'])
            elif (_controller['action'] == 'new company'):
                result_create = _controller['controller']._client.companies.create_company(
                    {'name': 'my company'}).json()
                result = _controller['controller'].get_item(_controller['action'], result_create['companyId'])
                self.assertEqual(result_create['companyId'], result['companyId'])
                _controller['controller']._client.companies.delete_company(result_create['companyId'])
            elif (_controller['action'] == 'new deal'):
                result_create = _controller['controller']._client.deals.create_deal(
                {'dealname': 'my deal'}).json()
                result = _controller['controller'].get_item(_controller['action'], result_create['dealId'])
                self.assertEqual(result_create['dealId'], result['dealId'])
                _controller['controller']._client.deals.delete_deal(result_create['dealId'])

    def test_download_to_store_data(self):
        for _controller in self._list_source_controllers:
            result = _controller['controller'].download_to_stored_data(
                _controller['plug'].connection.related_connection, _controller['plug'])
            self.assertIn('downloaded_data', result)
            self.assertIsInstance(result['downloaded_data'], list)
            self.assertIsInstance(result['downloaded_data'][-1], dict)
            self.assertIn('identifier', result['downloaded_data'][-1])
            self.assertIsInstance(result['downloaded_data'][-1]['identifier'], dict)
            self.assertIn('name', result['downloaded_data'][-1]['identifier'])
            self.assertIn('value', result['downloaded_data'][-1]['identifier'])
            self.assertIsInstance(result['downloaded_data'][-1], dict)
            self.assertIn('raw', result['downloaded_data'][-1])
            self.assertIsInstance(result['downloaded_data'][-1]['raw'], str)
            self.assertIn('is_stored', result['downloaded_data'][-1])
            self.assertIsInstance(result['downloaded_data'][-1]['is_stored'], bool)
            self.assertIn('last_source_record', result)
            self.assertIsNotNone(result['last_source_record'])

    def test_download_source_data(self):
        for _controller in self._list_source_controllers:
            _count = 0
            result = _controller['controller'].download_source_data(_controller['plug'].connection.related_connection,
                                                                    _controller['plug'])
            count_end = StoredData.objects.filter(connection=self.connection_source, plug=_controller['plug']).count()
            self.assertNotEqual(count_end, _count)
            self.assertTrue(result)
            _count = _count + count_end

    def test_get_target_fiels(self):
        for _controller in self._list_target_controllers:
            result = _controller['controller'].get_target_fields()
            self.assertIsInstance(result, list)
            self.assertIsInstance(result[0], dict)

    def test_get_mapping_fields(self):
        for _controller in self._list_target_controllers:
            result = _controller['controller'].get_mapping_fields()
            self.assertIsInstance(result, list)
            self.assertIsInstance(result[0], MapField)

    def test_insert_data(self):
        """
        Verificar que TEST_HUBSPOT_EMAIL no exista en la instancia de hubspot.
        :return:
        """
        data = {'create contact':{'email':os.environ.get('TEST_HUBSPOT_EMAIL')}, 'create company': {'name': 'my company'}, 'create deal': {'dealname': 'my deal'}}
        for _controller in self._list_target_controllers:

            result = _controller['controller'].insert_data(data[_controller['action']], _controller['action'])
            self.assertIsInstance(result, dict)
            self.assertIn('id', result)
            self.assertIn('response', result)
            if _controller['action'] == 'create contact':
                _controller['controller']._client.contacts.delete_contact(result['response']['vid'])
            elif _controller['action'] == 'create company':
                _controller['controller']._client.companies.delete_company(result['response']['companyId'])
            elif _controller['action'] == 'create deal':
                _controller['controller']._client.deals.delete_deal(result['response']['dealId'])

    def test_send_stored_data(self):
        """
        Verificar que TEST_HUBSPOT_EMAIL no exista en la instancia de hubspot.
        :return:
        """
        data = {'create contact': {'email': os.environ.get('TEST_HUBSPOT_EMAIL')},
                'create company': {'name': 'my company'}, 'create deal': {'dealname': 'my deal'}}
        for _controller in self._list_target_controllers:
            data_list = [OrderedDict(data[_controller['action']])]
            result = _controller['controller'].send_stored_data(data_list)
            self.assertIsInstance(result, list)
            self.assertIsInstance(result[-1], dict)
            self.assertIn('data', result[-1])
            self.assertIn('response', result[-1])
            self.assertIn('sent', result[-1])
            self.assertIn('identifier', result[-1])
            self.assertIsInstance(result[-1]['data'], dict)
            self.assertIsInstance(result[-1]['sent'], bool)
            self.assertEqual(result[-1]['data'], dict(data_list[0]))
            if _controller['action'] == 'create contact':
                _controller['controller']._client.contacts.delete_contact(result[-1]['identifier'])
            elif _controller['action'] == 'create company':
                _controller['controller']._client.companies.delete_company(result[-1]['identifier'])
            elif _controller['action'] == 'create deal':
                _controller['controller']._client.deals.delete_deal(result[-1]['identifier'])

    def test_send_target_data(self):
        """
        Verificar que TEST_HUBSPOT_EMAIL no exista en la instancia de hubspot.
        :return:
        """
        data = {'create contact': {'email': os.environ.get('TEST_HUBSPOT_EMAIL')},
                'create company': {'name': 'my company'}, 'create deal': {'dealname': 'my deal'}}
        fields = {'create contact': 'email', 'create company': 'name', 'create deal': 'dealname'}
        for _controller in self._list_target_controllers:
            _count = 0
            _source_data = [{'id': 1, 'data': data[_controller['action']]}]
            _target_fields = {fields[_controller['action']]: '%%{0}%%'.format(fields[_controller['action']])}
            _target = OrderedDict(_target_fields)
            result = _controller['controller'].send_target_data(source_data=_source_data, target_fields=_target)
            count_history = SendHistory.objects.all().count()
            self.assertNotEqual(count_history, _count)
            _count = _count + count_history
            if _controller['action'] == 'create contact':
                _controller['controller']._client.contacts.delete_contact(result[0])
            elif _controller['action'] == 'create company':
                _controller['controller']._client.companies.delete_company(result[0])
            elif _controller['action'] == 'create deal':
                _controller['controller']._client.deals.delete_deal(result[0])