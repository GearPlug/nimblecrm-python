import os
import re
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.crm import ActiveCampaignController
from apps.gp.models import Connection, ActiveCampaignConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Webhook, StoredData, Gear, GearMap, GearMapData
from apps.history.models import DownloadHistory

class ActiveCampaignControllerTestCases(TestCase):
    """
        TEST_ACTIVECAMPAIGN_HOST : String: Host registrado en Active Campaign
        TEST_ACTIVECAMPAIGN_KEY : String: Key de la API
        TEST_ACTIVECAMPAIGN_LIST: String: ID de la lista donde se creará o leerá un contacto
        TEST_ACTIVECAMPAIGN_EMAIL: String: email, para realizar pruebas, este email no debe estar registrado en la aplicación.
    """
    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.ActiveCampaign.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        _connection_source = {
            "connection": cls.connection_source,
            "name": "ConnectionTest Source",
            "host": os.environ.get("TEST_ACTIVECAMPAIGN_HOST"),
            "connection_access_key": os.environ.get("TEST_ACTIVECAMPAIGN_KEY"),
        }
        cls.activecampaign_connection_source = ActiveCampaignConnection.objects.create(**_connection_source)

        cls.connection_target = Connection.objects.create(**connection)

        _connection_target = {
            "connection": cls.connection_target,
            "name": "ConnectionTest Target",
            "host": os.environ.get("TEST_ACTIVECAMPAIGN_HOST"),
            "connection_access_key": os.environ.get("TEST_ACTIVECAMPAIGN_KEY"),
        }
        cls.activecampaign_connection_target = ActiveCampaignConnection.objects.create(**_connection_target)

        _list_source_actions = ['new contact', 'new subscriber', 'unsubscribed contact']

        cls._list_source_plugs = []

        for action in _list_source_actions:
            action_source = Action.objects.get(connector_id=ConnectorEnum.ActiveCampaign.value, action_type="source",
                                           name=action, is_active=True)
            activecampaign_plug_source = {
                "name": "PlugTest Source",
                "connection": cls.connection_source,
                "action": action_source,
                "plug_type": "source",
                "user": cls.user,
                "is_active": True
            }
            _source_plug = Plug.objects.create(**activecampaign_plug_source)
            if action in ['new subscriber', 'unsubscribed contact']:
                _specification_source = ActionSpecification.objects.get(action=action_source, name="list")
                action_specification_source = {
                    "plug": _source_plug,
                    "action_specification": _specification_source,
                    "value": os.environ.get("TEST_ACTIVECAMPAIGN_LIST")
                }
                PlugActionSpecification.objects.create(**action_specification_source)
            else:
                _specification_source = ""
            cls._list_source_plugs.append({'action': action, 'plug':_source_plug, 'specification': _specification_source})

        _list_target_actions = ['subscribe contact', 'unsubscribe contact', 'create contact']
        cls._list_target_plugs = []

        for action in _list_target_actions:
            action_target = Action.objects.get(connector_id=ConnectorEnum.ActiveCampaign.value, action_type="target",
                                           name=action, is_active=True)
            active_campaign_plug_target = {
                "name": "PlugTest Target",
                "connection": cls.connection_target,
                "action": action_target,
                "plug_type": "target",
                "user": cls.user,
                "is_active": True
            }
            _plug_target = Plug.objects.create(**active_campaign_plug_target)
            _specification_target = ActionSpecification.objects.get(action=action_target, name="list")
            action_specification_target = {
                "plug": _plug_target,
                "action_specification": _specification_target,
                "value": os.environ.get("TEST_ACTIVECAMPAIGN_LIST")
            }
            PlugActionSpecification.objects.create(**action_specification_target)
            cls._list_target_plugs.append({'action': action, 'plug': _plug_target, 'specification': _specification_target})

        # gear = {
        #     "name": "Gear 1",
        #     "user": cls.user,
        #     "source": cls.plug_source,
        #     "target": cls.plug_target,
        #     "is_active": True
        # }
        # cls.gear = Gear.objects.create(**gear)
        # cls.gear_map = GearMap.objects.create(gear=cls.gear)
        #
        # map_data_1 = {"target_name": "email", "source_value": "%%email%%", "gear_map": cls.gear_map}
        # map_data_2 = {"target_name": "first_name", "source_value": "%%first_name%%", "gear_map": cls.gear_map}
        # map_data_3 = {"target_name": "last_name", "source_value": "%%last_name%%", "gear_map": cls.gear_map}
        # map_data_4 = {"target_name": "phone", "source_value": "%%phone%%", "gear_map": cls.gear_map}
        # map_data_5 = {"target_name": "orgname", "source_value": "%%orgname%%", "gear_map": cls.gear_map}
        # GearMapData.objects.create(**map_data_1)
        # GearMapData.objects.create(**map_data_2)
        # GearMapData.objects.create(**map_data_3)
        # GearMapData.objects.create(**map_data_4)
        # GearMapData.objects.create(**map_data_5)

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self._list_source_controllers = []
        self._list_target_controllers = []
        for _plug in self._list_source_plugs:
            _my_plug = _plug['plug']
            source_controller = ActiveCampaignController(_plug['plug'].connection.related_connection, _plug['plug'])
            self._list_source_controllers.append({'action':_plug['action'], 'controller': source_controller,
                                                  'plug': _plug['plug'], 'specification': _plug['specification']})
        for _plug in self._list_target_plugs:
            target_controller = ActiveCampaignController(_plug['plug'].connection.related_connection, _plug['plug'])
            self._list_target_controllers.append({'action': _plug['action'], 'controller': target_controller,
                                                  'plug':_plug['plug'], 'specification': _plug['specification']})

    def get_hooks(self):
        return  {"contact[tags]": [""], "contact[phone]": ["325 7048546"], "initiated_from": ["admin"],
         "contact[orgname]": ["Organization1"], "contact[first_name]": ["Miguel"],
         "contact[ip]": ["0.0.0.0"], "contact[email]": [os.environ.get("TEST_ACTIVECAMPAIGN_EMAIL")],
         "initiated_by": ["admin"], "orgname": ["Organization1"], "type": ["subscribe"], "list": ["0"],
         "date_time": ["2017-09-21T11:33:13-05:00"], "contact[last_name]": ["Ferrer"],
         "contact[id]": ["36"]}

    def _get_fields(self, action):
        if action == 'unsubscribe a contact':
            return [{'name': 'email', 'label': 'Email', 'type': 'varchar', 'required': True}]
        else:
            return [
                {'name': 'email', 'label': 'Email', 'type': 'varchar', 'required': True},
                {'name': 'first_name', 'label': 'First Name', 'type': 'varchar', 'required': False},
                {'name': 'last_name', 'label': 'Last Name', 'type': 'varchar', 'required': False},
                {'name': 'phone', 'label': 'Phone', 'type': 'varchar', 'required': False},
                {'name': 'orgname', 'label': 'Organization Name', 'type': 'varchar', 'required': False},
            ]

    def _clean_data(self, POST):
        formatted = {k: v[0] for k, v in POST.items() if type(v) == list and len(v) < 2}
        expr = "\[(.*?)\]"
        clean_data = {}
        for k, v in formatted.items():
            m = re.search(expr, k)
            if m:
                key = m.group(1)
            else:
                key = k
            if key not in clean_data:
                clean_data[key] = v
        return clean_data

    # def test_controller(self):
    #     """
    #     Comprueba que los atributos del controlador esten instanciados
    #     """
    #     _total_controllers = self._list_source_controllers + self._list_target_controllers
    #     for _controller in _total_controllers:
    #         self.assertIsInstance(_controller['controller']._connection_object, ActiveCampaignConnection)
    #         self.assertIsInstance(_controller['controller']._plug, Plug)
    #         self.assertTrue(_controller['controller']._client)
    #
    # def test_test_connection(self):
    #     _total_controllers = self._list_source_controllers + self._list_target_controllers
    #     for _controller in _total_controllers:
    #         result = _controller['controller'].test_connection()
    #         self.assertTrue(result)
    #
    # def test_get_lists(self):
    #     """Método que testea que traiga las listas de contactos de Active Campaig, el parámetro TEST_ACTIVECAMPAIGN_LIST debe
    #     ser un ID de una lista existente en la cuenta perteneciente a las credenciales de entrada"""
    #     _total_controllers = self._list_source_controllers + self._list_target_controllers
    #     for _controller in _total_controllers:
    #         if _controller['action'] in ['new subscriber', 'unsubscribed contact', 'subscribe contact', 'unsubscribe contact']:
    #             _list = None
    #             result = _controller['controller'].get_lists()
    #             for i in result:
    #                 if i["id"] == os.environ.get("TEST_ACTIVECAMPAIGN_LIST"):
    #                     _list = i["id"]
    #             self.assertEqual(_list, os.environ.get("TEST_ACTIVECAMPAIGN_LIST"))

    # def test_get_action_specification_options(self):
    #     """Testea que retorne los action specification de manera correcta, en este caso son las listas de contactos"""
    #     _total_controllers = self._list_source_controllers + self._list_target_controllers
    #     for _controller in _total_controllers:
    #         if _controller in ['new subscriber', 'unsubscribed contact', 'subscribe contact', 'unsubscribe contact']:
    #             action_specification_id = _controller['specification'].id
    #             result = _controller['controller'].get_action_specification_options(action_specification_id)
    #             _list = None
    #             for i in result:
    #                 if i["id"] == os.environ.get("TEST_ACTIVECAMPAIGN_LIST"):
    #                     _list = i["id"]
    #             self.assertIsInstance(result, tuple)
    #             self.assertEqual(_list, os.environ.get("TEST_ACTIVECAMPAIGN_LIST"))

    # def test_get_mapping_fields(self):
    #     """Testea que retorne los Mapping Fields de manera correcta"""
    #     for _controller in self._list_target_controllers:
    #         result = _controller['controller'].get_mapping_fields()
    #         self.assertIsInstance(result, list)
    #         self.assertIsInstance(result[0], MapField)

    # def test_get_target_fiels(self):
    #     """Testea que retorne los campos de un contacto"""
    #     for _controller in self._list_target_controllers:
    #         result = _controller['controller'].get_target_fields()
    #         self.assertEqual(result, self._get_fields(_controller['action']))

    # def test_create_webhook(self):
    #     """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
    #     webhook de la aplicación"""
    #     for _controller in self._list_source_controllers:
    #         count_start = Webhook.objects.filter(plug=_controller['plug']).count()
    #         result = _controller['controller'].create_webhook()
    #         count_end = Webhook.objects.filter(plug=_controller['plug']).count()
    #         webhook = Webhook.objects.last()
    #         self.assertEqual(count_start + 1, count_end)
    #         self.assertTrue(result)
    #         _controller['controller']._client.webhooks.delete_webhook(webhook.generated_id)

    # def test_download_source_data(self):
    #     """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
    #     count_start = StoredData.objects.filter(connection=self.connection_source, plug=self.plug_source).count()
    #     data = self.hook
    #     data["email"] = os.environ.get("TEST_ACTIVECAMPAIGN_EMAIL")
    #     data = self._clean_data(data)
    #     count_data = len(data)
    #     result = self.controller_source.download_source_data(self.plug_source.connection.related_connection, self.plug_source, data=data)
    #     count_end = StoredData.objects.filter(connection=self.connection_source, plug=self.plug_source).count()
    #     history = DownloadHistory.objects.last()
    #     self.assertEqual(count_end, count_start + count_data)
    #     data2= str(data)
    #     self.assertEqual(history.raw, data2.replace("'", '"'))
    #     self.assertEqual(history.identifier, str({'name': 'id', 'value' : int(data["id"])}))
    #     self.assertTrue(result)
    #
    # def test_download_to_store_data(self):
    #     """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
    #     {'downloaded_data':[
    #         {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
    #          "is_stored": True | False},
    #          "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
    #         {...}, {...},
    #      "last_source_record":(%last_order_by_value)},}
    #     """
    #     data = self._clean_data(self.hook)
    #     result = self.controller_source.download_to_stored_data(self.plug_source.connection.related_connection, self.plug_source,
    #                                                      data=data)
    #     self.assertIn('downloaded_data', result)
    #     self.assertIsInstance(result['downloaded_data'], list)
    #     self.assertIsInstance(result['downloaded_data'][-1], dict)
    #     self.assertIn('identifier', result['downloaded_data'][-1])
    #     self.assertIsInstance(result['downloaded_data'][-1]['identifier'], dict)
    #     self.assertIn('name', result['downloaded_data'][-1]['identifier'])
    #     self.assertIn('value', result['downloaded_data'][-1]['identifier'])
    #     self.assertIsInstance(result['downloaded_data'][-1], dict)
    #     self.assertIn('raw', result['downloaded_data'][-1])
    #     self.assertIsInstance(result['downloaded_data'][-1]['raw'], dict)
    #     self.assertIn('is_stored', result['downloaded_data'][-1])
    #     self.assertIsInstance(result['downloaded_data'][-1]['is_stored'], bool)
    #     self.assertIn('last_source_record', result)
    #     self.assertIsNotNone(result['last_source_record'])
    #
    def test_send_stored_data(self):
        """Simula un dato de entrada (data), este dato trae un email que no existe en la aplicacion
        (TEST_ACTIVECAMPAIGN_EMAIL), verifica que el contacto se crea en la aplicación y que el método
        retorna una lista de acuerdo a:
        {'data': {(%dict del metodo 'get_dict_with_source_data')},
         'response': (%mensaje del resultado),
         'sent': True|False,
         'identifier': (%identificador del dato enviado. Ej: ID.)
        }
        Al final se borra el contacto de la aplicación.
        """
        for _controller in self._list_target_controllers:
            if _controller['action'] == 'unsubscribe contact':
                _controller['controller']._client.contacts.create_contact({'email':os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')})
            data = {'email': os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')}
            data_list = [OrderedDict(data)]
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
            result_view = _controller['controller']._client.contacts.view_contact(result[-1]['identifier'])
            self.assertEqual(result_view['result_code'],1)
            self.assertEqual(result_view['email'], os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL'))
            _controller['controller']._client.contacts.delete_contact(result[-1]['identifier'])
    #
    #
    # def test_get_custom_fields(self):
    #     """Testea que se retorne los custom fields de un contacto"""
    #     result = self.controller_source.get_custom_fields()
    #     self.assertIsInstance(result, dict)
    #
    # def test_do_webhook_process(self):
    #     """Simula un dato de entrada (self.hook), se crea un webhook y se verifica que retorne
    #     un status code =200, al final se borra el webhook"""
    #     self.controller_source.create_webhook()
    #     webhook = Webhook.objects.last()
    #     result = self.controller_source.do_webhook_process(POST=self.hook, webhook_id=webhook.id)
    #     self.assertEqual(result.status_code, 200)
    #     self.controller_source._client.webhooks.delete_webhook(webhook.generated_id)
