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
from apps.history.models import DownloadHistory, SendHistory


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

        _list_source_actions = ['new contact', 'new subscriber', 'unsubscribed contact', 'new task', 'new deal', 'task completed', 'deal updated']

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
            cls._list_source_plugs.append(
                {'action': action, 'plug': _source_plug, 'specification': _specification_source})

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
            cls._list_target_plugs.append(
                {'action': action, 'plug': _plug_target, 'specification': _specification_target})

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
            source_controller = ActiveCampaignController(_plug['plug'].connection.related_connection, _plug['plug'])
            self._list_source_controllers.append({'action': _plug['action'], 'controller': source_controller,
                                                  'plug': _plug['plug'], 'specification': _plug['specification'],
                                                  'gear': _plug['gear'], 'gear_map': _plug['gear_map']})
        for _plug in self._list_target_plugs:
            target_controller = ActiveCampaignController(_plug['plug'].connection.related_connection, _plug['plug'])
            self._list_target_controllers.append({'action': _plug['action'], 'controller': target_controller,
                                                  'plug': _plug['plug'], 'specification': _plug['specification']})

    def _get_hooks(self, action):
        if action == 'new contact':
            return {'initiated_by': ['admin'], 'contact[tags]': [''], 'date_time': ['2017-11-27T12:51:37-06:00'],
                    'list': ['0'], 'contact[email]': ['daysy@grplug.com'], 'contact[phone]': [''],
                    'type': ['subscribe'],
                    'initiated_from': ['admin'], 'contact[last_name]': [''],
                    'contact[id]': ['119'], 'orgname': [''], 'contact[ip]': ['0.0.0.0'],
                    'contact[orgname]': [''], 'contact[first_name]': ['']}

        elif action == 'new subscriber':
            return {'initiated_by': ['admin'], 'contact[first_name]': ['Lelia2'], 'orgname': [''],
                    'contact[phone]': [''], 'list': ['1'],
                    'initiated_from': ['admin'], 'type': ['subscribe'], 'contact[last_name]': ['Rubiano'],
                    'contact[id]': ['10'],
                    'contact[ip]': ['0.0.0.0'], 'date_time': ['2017-11-24T08:50:26-06:00'], 'contact[orgname]': [''],
                    'contact[email]': ['lrubianotest@grplug.com'], 'contact[tags]': ['']}
        elif action == 'unsubscribed contact':
            return {'type': ['unsubscribe'], 'list': ['1'], 'account_id': ['474042'], 'contact[id]': ['10'],
                    'initiated_from': ['admin'], 'contact[tags]': [''], 'initiated_by': ['admin'],
                    'contact[phone]': [''], 'date_time': ['2017-11-24T09:33:27-06:00'], 'contact[orgname]': [''],
                    'orgname': [''], 'contact[first_name]': ['Lelia2'], 'contact[ip]': ['0.0.0.0'],
                    'contact[email]': ['lrubianotest@grplug.com'], 'contact[last_name]': ['Rubiano']}
        elif action == 'new task':
            return {'deal[orgname]': [''],
                    'deal[pipeline_title]': ['my_pipeline'],
                    'deal[owner_firstname]': ['TestGearplug'],
                    'deal[contact_lastname]': ['Rubiano'],
                    'initiated_by': ['admin'],
                    'task[edate]': ['2017-11-25 11:15:00'],
                    'date_time': ['2017-11-24T10:09:32-06:00'],
                    'contact[ip]': ['0.0.0.0'],
                    'deal[contactid]': ['9'],
                    'contact[orgname]': [''],
                    'task[title]': [''],
                    'deal[contact_firstname]': ['Lelia'],
                    'task[type_id]': ['1'],
                    'task[edate_iso]': ['2017-11-25T11:15:00-06:00'],
                    'list': ['0'],
                    'contact[id]': ['9'],
                    'deal[create_date_iso]': ['2017-11-24T10:06:22-06:00'],
                    'deal[pipelineid]': ['1'],
                    'deal[owner_lastname]': [''],
                    'deal[orgid]': ['0'],
                    'deal[stageid]': ['1'],
                    'deal[value]': ['100.00'],
                    'type': ['deal_task_add'],
                    'task[type_title]': ['Call'],
                    'task[note]': ['task1'],
                    'task[id]': ['1'],
                    'contact[phone]': [''],
                    'task[duedate]': ['2017-11-25 11:00:00'],
                    'deal[status]': ['0'],
                    'orgname': [''],
                    'deal[contact_email]': ['lrubiano@grplug.com'],
                    'deal[owner]': ['1'],
                    'deal[currency]': ['usd'],
                    'contact[email]': ['lrubiano@grplug.com'],
                    'contact[last_name]': ['Rubiano'],
                    'task[duedate_iso]': ['2017-11-25T11:00:00-06:00'],  # Fecha de inicio de la tarea
                    'initiated_from': ['admin'],
                    'deal[stage_title]': ['To Contact'],
                    'deal[title]': ['deal1'],
                    'contact[tags]': [''],
                    'deal[currency_symbol]': ['$'],
                    'contact[first_name]': ['Lelia'],
                    'deal[value_raw]': ['100'],
                    'deal[create_date]': ['2017-11-24 10:06:22'],
                    'deal[id]': ['1']}
        elif action == 'new deal':
            return {'initiated_from': ['admin'],
                    'deal[pipeline_title]': ['my_pipeline'],
                    'deal[contact_email]': ['lrubiano@grplug.com'],
                    'deal[orgname]': [''],
                    'deal[contact_lastname]': ['Rubiano'],
                    'initiated_by': ['admin'],
                    'contact[phone]': [''],
                    'date_time': ['2017-11-24T10:06:22-06:00'],
                    'deal[owner]': ['1'],
                    'deal[contactid]': ['9'],
                    'contact[orgname]': [''],
                    'orgname': [''],
                    'deal[owner_firstname]': ['TestGearplug'],
                    'deal[contact_firstname]': ['Lelia'],
                    'contact[ip]': ['0.0.0.0'],
                    'deal[id]': ['1'],
                    'deal[currency]': ['usd'],
                    'contact[email]': ['lrubiano@grplug.com'],
                    'contact[last_name]': ['Rubiano'],
                    'deal[stageid]': ['1'],
                    'deal[stage_title]': ['To Contact'],
                    'type': ['deal_add'], 'list': ['0'],
                    'deal[title]': ['deal1'],
                    'contact[id]': ['9'],
                    'deal[create_date_iso]': ['2017-11-24T10:06:22-06:00'],
                    'deal[pipelineid]': ['1'], 'contact[tags]': [''],
                    'deal[currency_symbol]': ['$'],
                    'deal[orgid]': ['0'],
                    'deal[status]': ['0'],
                    'contact[first_name]': ['Lelia'],
                    'deal[value_raw]': ['100'],
                    'deal[owner_lastname]': [''],
                    'deal[value]': ['100.00'],
                    'deal[create_date]': ['2017-11-24 10:06:22']}
        elif action == 'task completed':
            return {'deal[orgname]': [''], 'deal[title]': ['dealmm'], 'deal[currency_symbol]': ['$'],
                    'task[edate_iso]': ['2017-11-29T11:15:00-06:00'], 'task[donedate]': ['2017-11-28 08:59:17'],
                    'contact[tags]': [''], 'contact[fields][1]': ['field1'], 'task[duedate]': ['2017-11-29 11:00:00'],
                    'date_time': ['2017-11-28T08:59:17-06:00'], 'deal[value_raw]': ['100'],
                    'deal[pipeline_title]': ['my_pipeline'], 'deal[owner_firstname]': ['TestGearplug'],
                    'contact[orgname]': [''], 'type': ['deal_task_complete'],
                    'task[donedate_iso]': ['2017-11-28T08:59:17-06:00'], 'deal[currency]': ['usd'],
                    'deal[owner]': ['1'], 'contact[email]': ['diego@gmail.com'], 'task[type_id]': ['2'],
                    'task[type_title]': ['Email'], 'deal[status]': ['0'], 'deal[contact_lastname]': [''],
                    'contact[ip]': ['0.0.0.0'], 'initiated_by': ['admin'], 'deal[id]': ['3'],
                    'deal[contact_firstname]': ['diego@gmail.com'],
                    'deal[create_date_iso]': ['2017-11-24T14:23:00-06:00'], 'deal[value]': ['100.00'],
                    'deal[contact_email]': ['diego@gmail.com'], 'deal[stage_title]': ['To Contact'],
                    'deal[create_date]': ['2017-11-24 14:23:00'], 'task[edate]': ['2017-11-29 11:15:00'],
                    'deal[owner_lastname]': [''], 'deal[pipelineid]': ['1'], 'orgname': [''],
                    'task[duedate_iso]': ['2017-11-29T11:00:00-06:00'], 'contact[last_name]': [''],
                    'contact[phone]': [''], 'task[note]': ['MY TASK'], 'contact[id]': ['27'],
                    'contact[first_name]': ['diego@gmail.com'], 'contact[fields][2]': ['field2'], 'deal[orgid]': ['0'],
                    'task[id]': ['6'], 'task[title]': [''], 'deal[stageid]': ['1'], 'initiated_from': ['admin'],
                    'list': ['0'], 'deal[contactid]': ['27']}
        elif action == 'deal updated':
            return {'deal[orgname]': [''], 'deal[title]': ['deal5'],
                    'deal[create_date_iso]': ['2017-11-24T14:18:04-06:00'], 'deal[value]': ['100.00'],
                    'deal[contact_email]': ['diego@gmail.com'], 'updated_fields[3]': ['stage'],
                    'deal[stage_title]': ['To Contact'], 'deal[owner_lastname]': [''],
                    'deal[create_date]': ['2017-11-24 14:18:04'], 'deal[currency_symbol]': ['$'], 'contact[tags]': [''],
                    'deal[pipelineid]': ['1'], 'contact[fields][1]': ['field1'], 'deal[value_raw]': ['100'],
                    'deal[contact_firstname]': ['diego@gmail.com'], 'date_time': ['2017-11-28T09:03:08-06:00'],
                    'contact[id]': ['27'], 'orgname': [''], 'deal[pipeline_title]': ['my_pipeline'], 'list': ['0'],
                    'deal[owner_firstname]': ['TestGearplug'], 'contact[orgname]': [''], 'type': ['deal_update'],
                    'contact[last_name]': [''], 'contact[phone]': [''], 'deal[currency]': ['usd'],
                    'contact[first_name]': ['diego@gmail.com'], 'deal[owner]': ['1'], 'updated_fields[4]': ['contact'],
                    'contact[email]': ['diego@gmail.com'], 'updated_fields[0]': ['title'],
                    'contact[fields][2]': ['field2'], 'deal[orgid]': ['0'], 'deal[status]': ['0'],
                    'updated_fields[2]': ['nextdate'], 'updated_fields[1]': ['mdate'], 'deal[contact_lastname]': [''],
                    'contact[ip]': ['0.0.0.0'], 'deal[stageid]': ['1'], 'initiated_from': ['admin'],
                    'initiated_by': ['admin'], 'deal[contactid]': ['27'], 'deal[id]': ['2']}

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

    def _clean_data(self, POST, controller):
        clean_data = {}
        for k, v in POST.items():
            if "[" in k:
                m = k.split("[")
                key = m[0] + "_" + m[1].replace("]", "")
                if key == 'contact_fields':
                    custom_fields = controller.get_custom_fields()
                    key = custom_fields[str(int(m[2].replace("]", "")) - 1)]['label']
                clean_data[key] = v[0]
            else:
                clean_data[k] = v[0]
        return clean_data

    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        _total_controllers = self._list_source_controllers + self._list_target_controllers
        for _controller in _total_controllers:
            self.assertIsInstance(_controller['controller']._connection_object, ActiveCampaignConnection)
            self.assertIsInstance(_controller['controller']._plug, Plug)
            self.assertTrue(_controller['controller']._client)

    def test_test_connection(self):
        _total_controllers = self._list_source_controllers + self._list_target_controllers
        for _controller in _total_controllers:
            result = _controller['controller'].test_connection()
            self.assertTrue(result)

    def test_get_lists(self):
        """Método que testea que traiga las listas de contactos de Active Campaig, el parámetro TEST_ACTIVECAMPAIGN_LIST debe
        ser un ID de una lista existente en la cuenta perteneciente a las credenciales de entrada"""
        _total_controllers = self._list_source_controllers + self._list_target_controllers
        for _controller in _total_controllers:
            if _controller['action'] in ['new subscriber', 'unsubscribed contact', 'subscribe contact',
                                         'unsubscribe contact']:
                _list = None
                result = _controller['controller'].get_lists()
                for i in result:
                    if i["id"] == os.environ.get("TEST_ACTIVECAMPAIGN_LIST"):
                        _list = i["id"]
                self.assertEqual(_list, os.environ.get("TEST_ACTIVECAMPAIGN_LIST"))

    def test_get_action_specification_options(self):
        """Testea que retorne los action specification de manera correcta, en este caso son las listas de contactos"""
        _total_controllers = self._list_source_controllers + self._list_target_controllers
        for _controller in _total_controllers:
            if _controller in ['new subscriber', 'unsubscribed contact', 'subscribe contact', 'unsubscribe contact']:
                action_specification_id = _controller['specification'].id
                result = _controller['controller'].get_action_specification_options(action_specification_id)
                _list = None
                for i in result:
                    if i["id"] == os.environ.get("TEST_ACTIVECAMPAIGN_LIST"):
                        _list = i["id"]
                self.assertIsInstance(result, tuple)
                self.assertEqual(_list, os.environ.get("TEST_ACTIVECAMPAIGN_LIST"))

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        for _controller in self._list_target_controllers:
            result = _controller['controller'].get_mapping_fields()
            self.assertIsInstance(result, list)
            self.assertIsInstance(result[0], MapField)

    def test_get_target_fiels(self):
        """Testea que retorne los campos de un contacto"""
        for _controller in self._list_target_controllers:
            result = _controller['controller'].get_target_fields()
            self.assertEqual(result, self._get_fields(_controller['action']))

    def test_create_webhook(self):
        """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
        webhook de la aplicación"""
        for _controller in self._list_source_controllers:
            count_start = Webhook.objects.filter(plug=_controller['plug']).count()
            result = _controller['controller'].create_webhook()
            count_end = Webhook.objects.filter(plug=_controller['plug']).count()
            webhook = Webhook.objects.last()
            self.assertEqual(count_start + 1, count_end)
            self.assertTrue(result)
            _controller['controller']._client.webhooks.delete_webhook(webhook.generated_id)

    def test_download_source_data(self):
        """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
        for _controller in self._list_source_controllers:
            data = self._get_hooks(_controller['action'])
            data = self._clean_data(data, _controller['controller'])

            count_data = len(data)
            result = _controller['controller'].download_source_data(_controller['plug'].connection.related_connection,
                                                                    _controller['plug'], data=data)
            count_end = StoredData.objects.filter(connection=self.connection_source, plug=_controller['plug']).count()
            if _controller['action'] in ['new task', 'task completed']:
                count_data += 4
            elif _controller['action'] in ['new deal', 'deal updated']:
                count_data = count_data+2
            self.assertEqual(count_end, count_data)
            self.assertTrue(result)

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        for _controller in self._list_source_controllers:
            data = self._clean_data(self._get_hooks(_controller['action']), _controller['controller'])
            result = _controller['controller'].download_to_stored_data(
                _controller['plug'].connection.related_connection, _controller['plug'],
                data=data)
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
                _controller['controller']._client.contacts.create_contact(
                    {'email': os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')})
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
            self.assertEqual(result_view['result_code'], 1)
            self.assertEqual(result_view['email'], os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL'))
            _controller['controller']._client.contacts.delete_contact(result[-1]['identifier'])

    def test_get_custom_fields(self):
        """Testea que se retorne los custom fields de un contacto"""
        for _controller in self._list_source_controllers:
            if _controller['action'] in ['subscribe contact', 'unsubscribe contact', 'create contact']:
                result = _controller['controller'].get_custom_fields()
                self.assertIsInstance(result, dict)

    def test_do_webhook_process(self):
        """Simula un dato de entrada (self.hook), se crea un webhook y se verifica que retorne
        un status code =200, al final se borra el webhook"""
        for _controller in self._list_source_controllers:
            _controller['controller'].create_webhook()
            webhook = Webhook.objects.last()
            data = self._get_hooks(_controller['action'])
            for k, v in data.items():
                data[k] = v[0]
            result = _controller['controller'].do_webhook_process(POST=data, webhook_id=webhook.id)
            self.assertEqual(result.status_code, 200)
            _controller['controller']._client.webhooks.delete_webhook(webhook.generated_id)

    def test_send_target_data(self):
        """Verifica que se cree el registro ingresado en la tabla Sendstoredata, al final se borra
        el contacto de la aplicación"""
        _source_data = [{'id': 1, 'data': {'email': os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')}}]
        _target_fields = {'email': '%%email%%'}
        for _controller in self._list_target_controllers:
            if _controller['action'] == 'unsubscribe contact':
                _controller['controller']._client.contacts.create_contact(
                    {'email': os.environ.get('TEST_ACTIVECAMPAIGN_EMAIL')})
            _target = OrderedDict(_target_fields)
            result = _controller['controller'].send_target_data(source_data=_source_data, target_fields=_target)
            count_history = SendHistory.objects.all().count()
            self.assertNotEqual(count_history, 0)
            _controller['controller']._client.contacts.delete_contact(result[0])
