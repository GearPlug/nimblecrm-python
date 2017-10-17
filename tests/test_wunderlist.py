import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, WunderListConnection, Plug, Action, \
    ActionSpecification, PlugActionSpecification, Gear, StoredData, Webhook
from apps.gp.controllers.ofimatic import WunderListController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict
from apps.history.models import DownloadHistory, SendHistory

class WunderlistControllerTestCases(TestCase):
    """
    TEST_WUNDERLIST_TOKEN: String:
    TEST_WUNDERLIST_LIST: String, ID de una lista existente en la aplicación
    TEST_WUNDERLIST_USER: String, ID de un usuario existente en la aplicación
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='lrubiano@grplug.com',
                                       email='lrubiano@grplug.com',
                                       password='Prueba#2017')
        _dict_source_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.WunderList.value
        }
        cls.source_connection = Connection.objects.create(**_dict_source_connection)

        _dict_target_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.WunderList.value
        }
        cls.target_connection = Connection.objects.create(**_dict_target_connection)

        _dict_wunderlist_source_connection = {
            'connection': cls.source_connection,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_WUNDERLIST_TOKEN'),
        }
        cls.wunderlist_source_connection = WunderListConnection.objects.create(**_dict_wunderlist_source_connection)

        _dict_wunderlist_target_connection = {
            'connection': cls.target_connection,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_WUNDERLIST_TOKEN'),
        }
        cls.wunderlist_target_connection = WunderListConnection.objects.create(**_dict_wunderlist_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.WunderList.value,
                                    action_type='source',
                                    name='new task',
                                    is_active=True)

        target_action = Action.objects.get(connector_id=ConnectorEnum.WunderList.value,
                                           action_type='target',
                                           name='create task',
                                           is_active=True)

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

        cls.source_specification = ActionSpecification.objects.get(action=source_action,
                                                         name='list')

        cls.target_specification = ActionSpecification.objects.get(action=target_action,
                                                               name='list')

        _dict_source_specification = {
            'plug': cls.plug_source,
            'action_specification': cls.source_specification,
            'value': os.environ.get('TEST_WUNDERLIST_LIST')
        }
        PlugActionSpecification.objects.create(**_dict_source_specification)

        _dict_target_specification = {
            'plug': cls.plug_target,
            'action_specification': cls.target_specification,
            'value': os.environ.get('TEST_WUNDERLIST_LIST')
        }
        PlugActionSpecification.objects.create(**_dict_target_specification)

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.
        """
        self.source_controller = WunderListController(
            self.plug_source.connection.related_connection, self.plug_source)

        self.target_controller = WunderListController(
            self.plug_target.connection.related_connection, self.plug_target)

        self.hook = {'cause': None, 'enqueued_at': 1507932416.8459098, 'subject': {'parents': [{'type': 'list', 'id': 304896051}], 'type': 'task', 'revision': 1, 'id': 3199763388, 'previous_revision': 0}, 'user_id': 59819071, 'before': {'revision': 0}, 'client': {'device_id': 'a1a82c69-93c0-4a58-a994-95306c281d68', 'user_id': '59819071', 'request_id': 'lw93ea96f9278338a745bc6b5e45a1da', 'id': '498d3ffc44ddfa2f275b', 'instance_id': '9ae64ef5-d2af-41b7-9dc6-e42b-a35db49f'}, 'operation': 'create', 'version': 1, 'type': 'mutation', 'after': {'created_by_id': 59819071, 'id': 3199763388, 'starred': False, 'updated_at': '2017-10-13T22:06:56.818Z', 'is_recurrence_child': False, 'title': 'prueba1', 'completed': False, 'revision': 1, 'created_at': '2017-10-13T22:06:56.818Z', 'list_id': 304896051, 'created_by_request_id': '498d3ffc44ddfa2f275b:a1a82c69-93c0-4a58-a994-95306c281d68:9ae64ef5-d2af-41b7-9dc6-e42b-a35db49f:59819071:lw93ea96f9278338a745bc6b5e45a1da'}, 'data': {'created_by_id': 59819071, 'id': 3199763388, 'starred': False, 'updated_at': '2017-10-13T22:06:56.818Z', 'is_recurrence_child': False, 'title': 'prueba1', 'completed': False, 'revision': 1, 'created_at': '2017-10-13T22:06:56.818Z', 'list_id': 304896051, 'created_by_request_id': '498d3ffc44ddfa2f275b:a1a82c69-93c0-4a58-a994-95306c281d68:9ae64ef5-d2af-41b7-9dc6-e42b-a35db49f:59819071:lw93ea96f9278338a745bc6b5e45a1da'}}

        self.data = {'title': 'task_test', 'assignee_id': str({'id': os.environ.get('TEST_WUNDERLIST_USER'), 'name': 'GearPlug'})}

    def _get_fields(self):
        users = self.target_controller.get_users()
        return [{'name': 'title', 'type': 'text', 'required': True, 'label': 'Title'},
                {"name": "assignee_id", "required": False, "type": 'varchar',
                 "choices": users, 'label': 'Assignee'},
                ]

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.
        """
        self.assertIsInstance(self.source_controller._connection_object, WunderListConnection)
        self.assertIsInstance(self.target_controller._connection_object, WunderListConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)
        self.assertNotEqual(self.source_controller._token, None)
        self.assertNotEqual(self.target_controller._token, None)

    def test_test_connection(self):
        """Testea la conexión"""
        result = self.source_controller.test_connection()
        self.assertTrue(result)

    def test_get_lists(self):
        """Verifica que retorne todas las listas creadas en la aplicación"""
        result = self.source_controller.get_lists()
        _id_list = ""
        for r in result:
            if str(r['id']) == os.environ.get('TEST_WUNDERLIST_LIST'):
                _id_list = str(r['id'])
        self.assertEqual(_id_list, os.environ.get('TEST_WUNDERLIST_LIST'))

    def test_has_webhook(self):
        """Verifica que retorne True"""
        result = self.source_controller.has_webhook()
        self.assertTrue(result)

    def test_create_webhook(self):
        """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
        webhook de la aplicación"""
        result_create = self.source_controller.create_webhook()
        count_webhook= Webhook.objects.filter(plug=self.plug_source).count()
        webhook = Webhook.objects.last()
        result_view = self.source_controller.view_webhooks(os.environ.get('TEST_WUNDERLIST_LIST'))
        _create = False
        for r in result_view:
            if str(r['id']) == webhook.generated_id:
                _create = True
        result_delete = self.source_controller.delete_webhook(webhook.generated_id)
        self.assertEqual(count_webhook, 1)
        self.assertTrue(_create)

    def test_view_webhooks(self):
        """Verifica que retorne los parámetros de un webhook, se crea un webhook y se borra el final"""
        result_create = self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        result_view = self.source_controller.view_webhooks(os.environ.get('TEST_WUNDERLIST_LIST'))
        _view = False
        for r in result_view:
            if str(r['id']) == webhook.generated_id:
                _view = True
        self.source_controller.delete_webhook(webhook.generated_id)
        self.assertTrue(_view)

    def test_delete_webhook(self):
        """Verifica que se borre un webhook de la aplicación, para el procedimiento se crea primero el webhook"""
        self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        _delete = True
        self.source_controller.delete_webhook(webhook.generated_id)
        result_view = self.source_controller.view_webhooks(os.environ.get('TEST_WUNDERLIST_LIST'))
        for r in result_view:
            if str(r['id']) == webhook.generated_id:
                _delete = False
        self.assertTrue(_delete)

    def test_z_do_webhook_process(self):
        """Simula un dato de entrada (self.hook), se crea un webhook y se verifica que retorne
        un status code =200, al final se borra el webhook"""
        self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        result = self.source_controller.do_webhook_process(body=self.hook, webhook_id=webhook.id)
        self.assertEqual(result.status_code, 200)
        self.source_controller.delete_webhook(webhook.generated_id)

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection, self.plug_source,
                                                         task=self.hook)
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
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection, self.plug_source,
                                                             task=self.hook)
        count_store = StoredData.objects.filter(connection=self.source_connection, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        history_count = DownloadHistory.objects.all().count()
        self.assertNotEqual(count_store, 0)
        self.assertEqual(history.identifier, str({'name':'id', 'value': self.hook['subject']['id']}))
        self.assertEqual(history_count, 1)

    def test_create_task(self):
        """Verifica que se creee un tarea en la aplicación y en la lista TEST_WUNDERLIST_LIST, al final se borra la tarea"""
        result_create = self.target_controller.create_task(**self.data).json()
        result_view = self.target_controller.get_task(result_create['id'])
        self.assertIn('list_id', result_view)
        self.assertEqual(str(result_view['list_id']), os.environ.get('TEST_WUNDERLIST_LIST'))
        self.target_controller.delete_task(result_create['id'])

    def test_get_task(self):
        """Verifica que retorne los parámetros de una tarea, para probarlo primero se crea la taera y al final se borra"""
        result_create = self.target_controller.create_task(**self.data).json()
        result_view = self.target_controller.get_task(result_create['id'])
        self.assertIn('list_id', result_view)
        self.assertEqual(str(result_view['list_id']), os.environ.get('TEST_WUNDERLIST_LIST'))
        self.assertEqual(result_view['revision'], 1)
        self.target_controller.delete_task(result_create['id'])

    def test_delete_task(self):
        """Verifica """
        result_create = self.target_controller.create_task(**self.data).json()
        result_delete = self.target_controller.delete_task(result_create['id'])
        result_view = self.target_controller.get_task(result_create['id'])
        self.assertEqual(result_delete, 204)
        self.assertIn('error', result_view)

    def test_get_target_fields(self):
        """Verifica que retorne los campos de una tarea"""
        result = self.target_controller.get_target_fields()
        self.assertEqual(result, self._get_fields())
        self.assertIsInstance(result, list)

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.target_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_action_specification_options(self):
        """Testea que retorne los action specification de manera correcta los canales de la cuenta"""
        action_specification_id = self.target_specification.id
        result = self.target_controller.get_action_specification_options(action_specification_id)
        _list = None
        for i in result:
            if i["id"] == int(os.environ.get("TEST_WUNDERLIST_LIST")):
                _list = str(i["id"])
        self.assertIsInstance(result, tuple)
        self.assertEqual(_list, os.environ.get("TEST_WUNDERLIST_LIST"))

    def test_send_stored_data(self):
        """simula un dato de entrada y comprueba que retrorne una lista de acuerdo a los parámetros establecidos"""
        data_list=[OrderedDict(self.data)]
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
        self.target_controller.delete_task(result[-1]['identifier'])

    def test_get_users(self):
        """Verifica que retorne todos los usuarios de la aplicación"""
        result = self.target_controller.get_users()
        _user = None
        for r in result:
            if r['id'] == int(os.environ.get('TEST_WUNDERLIST_USER')):
                _user = str(r['id'])
        self.assertEqual(_user, os.environ.get('TEST_WUNDERLIST_USER'))


