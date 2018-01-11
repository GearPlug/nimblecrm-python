import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, AsanaConnection, Plug, Action, ActionSpecification, PlugActionSpecification, \
    Gear, GearMap, GearMapData, StoredData, Webhook
from apps.gp.controllers.project_management import AsanaController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict
from apps.history.models import DownloadHistory


class AsanaControllerTestCases(TestCase):
    """
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='nrincon@grplug.com', email='nrincon@grplug.com',
                                       password='Prueba#2017')
        _dict_source_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Asana.value
        }
        cls.source_connection = Connection.objects.create(**_dict_source_connection)

        _dict_target_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Asana.value
        }
        cls.target_connection = Connection.objects.create(**_dict_target_connection)
        _dict_asana_source_connection = {
            'connection': cls.source_connection,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_ASANA_TOKEN'),
            'refresh_token': os.environ.get('TEST_ASANA_REFRESH_TOKEN'),
            'token_expiration_timestamp': os.environ.get('TEST_ASANA_EXPIRATION_TOKEN'),
        }
        cls.asana_source_connection = AsanaConnection.objects.create(**_dict_asana_source_connection)
        _dict_asana_target_connection = {
            'connection': cls.target_connection,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_ASANA_TOKEN'),
            'refresh_token': os.environ.get('TEST_ASANA_REFRESH_TOKEN'),
            'token_expiration_timestamp': os.environ.get('TEST_ASANA_EXPIRATION_TOKEN'),
        }
        cls.bitbucket_target_connection = AsanaConnection.objects.create(**_dict_asana_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.Asana.value, action_type='source',
                                           name='new task created', is_active=True)

        target_action = Action.objects.get(connector_id=ConnectorEnum.Asana.value, action_type='target',
                                           name='create new task', is_active=True)

        _dict_source_action = {
            'name': 'PlugTest',
            'connection': cls.source_connection,
            'action': source_action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**_dict_source_action)

        _dict_target_action = {
            'name': 'PlugTest',
            'connection': cls.target_connection,
            'action': target_action,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**_dict_target_action)

        cls.source_specification = ActionSpecification.objects.get(action=source_action, name='project')

        cls.target_specification_1 = ActionSpecification.objects.get(action=target_action, name='workspace')
        cls.target_specification_2 = ActionSpecification.objects.get(action=target_action, name='project')

        _dict_source_specification = {
            'plug': cls.plug_source,
            'action_specification': cls.source_specification,
            'value': os.environ.get('TEST_ASANA_SOURCE_PROJECT')
        }
        PlugActionSpecification.objects.create(**_dict_source_specification)

        _dict_target_specification_1 = {
            'plug': cls.plug_target,
            'action_specification': cls.target_specification_1,
            'value': os.environ.get('TEST_ASANA_WORKSPACE_PROJECT')
        }
        PlugActionSpecification.objects.create(**_dict_target_specification_1)

        _dict_target_specification_2 = {
            'plug': cls.plug_target,
            'action_specification': cls.target_specification_2,
            'value': os.environ.get('TEST_ASANA_SOURCE_PROJECT')
        }
        PlugActionSpecification.objects.create(**_dict_target_specification_2)

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)

        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_1 = {'target_name': 'name', 'source_value': '%%name%%', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'completed', 'source_value': '%%completed%%', 'gear_map': cls.gear_map}

        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.
        """
        self.source_controller = AsanaController(
            self.plug_source.connection.related_connection, self.plug_source)

        self.target_controller = AsanaController(
            self.plug_target.connection.related_connection, self.plug_target)
        self.events = {"events": [
            {
                "resource": 518777122835931,
                "user": 512017988195276,
                "type": "task",
                "action": "changed",
                "created_at": "2018-01-10T14:44:58.552Z",
                "parent": None},
            ]}
        self.event = {
                "resource": 518777122835934,
                "user": 512017988195276,
                "type": "task",
                "action": "changed",
                "created_at": "2018-01-10T14:44:58.552Z",
                "parent": None
            }
        self.start_handshake = {
            'HTTP_X_HOOK_SECRET': '123456',
            'events': self.event
        }
        self.task = {
            "data": {
                "id": 518777122835931,
                "assignee": None,
                "assignee_status": "upcoming",
                "completed": False,
                "completed_at": None,
                "created_at": "2018-01-10T14:45:15.521Z",
                "due_at": None,
                "due_on": None,
                "followers":
                    [{
                        "id": 512017988195276,
                        "name": "Nerio Rincon"
                    }],
                "hearted": False,
                "hearts": [],
                "memberships":
                    [{"project":
                          {
                              "id": 518688910611337,
                              "name": "test_project_1"
                          },
                        "section": None
                    }],
                "modified_at": "2018-01-10T14:45:16.420Z",
                "name": "task 1",
                "notes": "",
                "num_hearts": 0,
                "parent": None,
                "projects":
                    [{
                        "id": 518688910611337,
                        "name": "test_project_1"
                    }],
                "tags": [],
                "workspace": {"id": 435324711031641, "name": "grplug.com"}
            }
        }
        self.task_id = {
            "resource": self.task['data']['id']
        }
        self.target_fields_manual = [{'name': 'asignee', 'type': 'text', 'required': False},
                {'name': 'completed', 'type': 'text', 'required': True},
                {'name': 'due_on', 'type': 'text', 'required': False},
                {'name': 'due_at', 'type': 'text', 'required': False},
                {'name': 'followers', 'type': 'text', 'required': False},
                {'name': 'hearted', 'type': 'text', 'required': False},
                {'name': 'name', 'type': 'text', 'required': True},
                {'name': 'notes', 'type': 'text', 'required': False},
                {'name': 'tags', 'type': 'text', 'required': False}]
        self.data_send = OrderedDict({'priority': 'trivial', 'status': 'new', 'title': 'try', 'kind': 'bug'})

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.
        """
        self.assertNotEqual(self.source_controller._connection_object, None)
        self.assertNotEqual(self.target_controller._connection_object, None)
        self.assertIsInstance(self.source_controller._connection_object, AsanaConnection)
        self.assertIsInstance(self.target_controller._connection_object, AsanaConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)

    def test_test_connection(self):
        """
        Verifica que la conexión este establecida
        """
        result = self.source_controller.test_connection()
        self.assertNotEqual(result, None)
        self.assertTrue(result)

    def test_get_user_information(self):
        """
        Resultado esperado:
        {
        'workspaces':
            [{
                'name': 'grplug.com',
                'id': 435324711031641
            }],
        'email': 'nrincon@grplug.com',
        'name': 'Nerio Rincon',
        'photo': None,
        'id': 512017988195276
        }
        :return:
        """
        response = self.source_controller.get_user_information()
        self.assertIsInstance(response, dict)
        self.assertIn('id', response)
        self.assertIn('email', response)
        self.assertIn('name', response)
        self.assertIn('workspaces', response)
        self.assertIsInstance(response['workspaces'], list)
        self.assertIsInstance(response['workspaces'][-1], dict)
        self.assertIn('id', response['workspaces'][-1])
        self.assertIn('name', response['workspaces'][-1])

    def test_do_webhook_process(self):
        """Simula un dato de entrada (self.hook), se crea un webhook y se verifica que retorne
        un status code =200"""
        self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        result_post = self.source_controller.do_webhook_process(META=self.start_handshake)
        result_body = self.source_controller.do_webhook_process(body=self.event, webhook_id=webhook.id)
        self.assertEqual(result_body.status_code, 200)
        self.assertEqual(result_post.status_code, 200)
        self.assertEqual(result_post.get(header='X-Hook-Secret') , self.start_handshake['HTTP_X_HOOK_SECRET'])

    def test_send_stored_data(self):
        """Testea que el método retorne los paŕametros establecidos"""
        data_list = [self.data_send]
        result = self.target_controller.send_stored_data(data_list)
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

    def test_get_workspaces(self):
        """
        Resultado esperado: [{'id': 435324711031641, 'name': 'grplug.com'}]
        :return:
        """
        response = self.source_controller.get_workspaces()
        self.assertIsInstance(response, list)
        self.assertIsInstance(response[-1], dict)
        self.assertIn('id', response[-1])
        self.assertIn('name', response[-1])

    def test_get_projects(self):
        """
        Resultado esperado: [{'data': [{'name': 'test_project_1', 'id': 518688910611337}]}]
        :return:
        """
        response = self.source_controller.get_projects()
        self.assertIsInstance(response, list)
        self.assertIsInstance(response[-1], dict)
        self.assertIn('data', response[-1])
        self.assertIsInstance(response[-1]['data'], list)
        self.assertIsInstance(response[-1]['data'][-1], dict)
        self.assertIn('name', response[-1]['data'][-1])
        self.assertIn('id', response[-1]['data'][-1])

    def test_create_task(self):
        """
        :return:
        """
        response = self.target_controller.create_task()
        self.assertIn('data', response)
        self.assertIn('id', response['data'])
        self.assertIn('created_at', response['data'])
        self.assertIn('created_at', response['data'])
        self.assertIsInstance(response['data']['workspace'], dict)
        self.assertIn('id', response['data']['workspace'])
        self.assertIn('name', response['data']['workspace'])

    def test_get_task(self):
        """
        :return:
        """
        response = self.source_controller.get_task(os.environ.get("TEST_ASANA_TASK"))
        self.assertIn('data', response.json())
        self.assertIn('created_at', response.json()['data'])
        self.assertIn('modified_at', response.json()['data'])
        self.assertIn('name', response.json()['data'])
        self.assertIn('id', response.json()['data'])

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result_1 = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, event=self.event)
        result_2 = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, event=self.events)
        self.assertIn('downloaded_data', result_1)
        self.assertIn('downloaded_data', result_2)
        self.assertIsInstance(result_1['downloaded_data'], list)
        self.assertIsInstance(result_2['downloaded_data'], list)
        self.assertIsInstance(result_1['downloaded_data'][-1], dict)
        self.assertIsInstance(result_2['downloaded_data'][-1], dict)
        self.assertIn('identifier', result_1['downloaded_data'][-1])
        self.assertIn('identifier', result_2['downloaded_data'][-1])
        self.assertIsInstance(result_1['downloaded_data'][-1]['identifier'], dict)
        self.assertIsInstance(result_2['downloaded_data'][-1]['identifier'], dict)
        self.assertIn('name', result_1['downloaded_data'][-1]['identifier'])
        self.assertIn('name', result_2['downloaded_data'][-1]['identifier'])
        self.assertIn('value', result_1['downloaded_data'][-1]['identifier'])
        self.assertIn('value', result_2['downloaded_data'][-1]['identifier'])
        self.assertIsInstance(result_1['downloaded_data'][-1], dict)
        self.assertIsInstance(result_2['downloaded_data'][-1], dict)
        self.assertIn('raw', result_1['downloaded_data'][-1])
        self.assertIn('raw', result_2['downloaded_data'][-1])
        self.assertIsInstance(result_1['downloaded_data'][-1]['raw'], dict)
        self.assertIsInstance(result_2['downloaded_data'][-1]['raw'], dict)
        self.assertIn('is_stored', result_1['downloaded_data'][-1])
        self.assertIn('is_stored', result_2['downloaded_data'][-1])
        self.assertIsInstance(result_1['downloaded_data'][-1]['is_stored'], bool)
        self.assertIsInstance(result_2['downloaded_data'][-1]['is_stored'], bool)
        self.assertIn('last_source_record', result_1)
        self.assertIn('last_source_record', result_2)
        self.assertIsNotNone(result_1['last_source_record'])
        self.assertIsNotNone(result_2['last_source_record'])
        self.assertIsNotNone(result_2['last_source_record'])


    def test_download_source_data(self):
        """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
        count_data = len(self.task['data'])
        self.source_controller.download_source_data(
            self.plug_source.connection.related_connection, self.plug_source, event=self.task_id)
        count_store = StoredData.objects.filter(connection=self.source_connection, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        # El contenido recibido en el download_to_stored_data() tiene valores anidados, se busca obtener un diccionario
        # de un solo nivel, por lo tanto se "sacan" o se "aplanan" los diccionarios, obteniendo incogruencias
        # a la hora de contar datos, por ende, se decide sumar al conteo de StoreData's la cantidad de valores
        # que se "aplanan"
        self.assertEqual(count_store+4, count_data)
        self.assertEqual(history.identifier, str({'name': 'id', 'value': self.task_id['resource']}))

    def test_get_target_fiels(self):
        """Testea que retorne los campos de un contacto"""
        result = self.target_controller.get_target_fields()
        self.assertEqual(result, self.target_fields_manual)

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.target_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

