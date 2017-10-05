import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, JiraConnection, Plug, Action, ActionSpecification, PlugActionSpecification, \
    Gear, GearMap, StoredData, GearMapData, Webhook, DownloadHistory
from apps.gp.controllers.project_management import JIRAController
from jira import JIRA as JiraClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class JiraControllerTestCases(TestCase):
    """
       Variables de entorno:
           TEST_JIRA_PROJECT: String: ID de un proyecto de la aplicación.
           TEST_JIRA_HOST: String: Host de la aplicación.
           TEST_JIRA_CONNECTION_USER: String: Usuario .
           TEST_JIRA_CONNECTION_PASSWORD: String: Contraseña .
    """

    fixtures = ['gp_base.json']
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.JIRA.value
        }
        cls.connection_source = Connection.objects.create(**_dict_connection)

        _dict_jira_connection_source = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'host': os.environ.get('TEST_JIRA_HOST'),
            'connection_user': os.environ.get('TEST_JIRA_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_JIRA_CONNECTION_PASSWORD')
        }
        cls.jira_connection_source = JiraConnection.objects.create(**_dict_jira_connection_source)

        cls.connection_target = Connection.objects.create(**_dict_connection)

        _dict_jira_connection_target = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'host': os.environ.get('TEST_JIRA_HOST'),
            'connection_user': os.environ.get('TEST_JIRA_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_JIRA_CONNECTION_PASSWORD')
        }
        cls.jira_connection_target = JiraConnection.objects.create(**_dict_jira_connection_target)

        action_source = Action.objects.get(connector_id=ConnectorEnum.JIRA.value, action_type='source',
                                           name='new issue', is_active=True)

        _dict_jira_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_source = Plug.objects.create(**_dict_jira_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.JIRA.value, action_type='target',
                                           name='create issue', is_active=True)

        _dict_jira_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_target = Plug.objects.create(**_dict_jira_plug_target)

        cls.specification_source = ActionSpecification.objects.get(action=action_source, name='project_id')
        cls.specification_target = ActionSpecification.objects.get(action=action_target, name='project_id')

        _dict_action_specification_source = {
            'plug': cls.plug_source,
            'action_specification': cls.specification_source,
            'value': os.environ.get('TEST_JIRA_PROJECT')
        }
        PlugActionSpecification.objects.create(**_dict_action_specification_source)

        _dict_action_specification_target = {
            'plug': cls.plug_target,
            'action_specification': cls.specification_target,
            'value': os.environ.get('TEST_JIRA_PROJECT')
        }
        PlugActionSpecification.objects.create(**_dict_action_specification_target)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_2 = {'target_name': 'summary', 'source_value': '%%summary%%', 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'priority', 'source_value': '3', 'gear_map': cls.gear_map}
        map_data_4 = {'target_name': 'issuetype', 'source_value': '10002', 'gear_map': cls.gear_map}
        map_data_5 = {'target_name': 'assignee', 'source_value': 'mferrer', 'gear_map': cls.gear_map}
        map_data_6 = {'target_name': 'description', 'source_value': '%%description%%', 'gear_map': cls.gear_map}
        map_data_7 = {'target_name': 'reporter', 'source_value': 'damanrique', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)
        GearMapData.objects.create(**map_data_4)
        GearMapData.objects.create(**map_data_5)
        GearMapData.objects.create(**map_data_6)
        GearMapData.objects.create(**map_data_7)

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        # self.client = Client()
        self.source_controller = JIRAController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = JIRAController(self.plug_target.connection.related_connection, self.plug_target)

        self.hook = {'issue': {'id': '12507', 'self': 'http://192.168.10.101/rest/api/2/issue/12507', 'key': 'PU-3', 'fields': {'aggregatetimeestimate': None, 'summary': 'JIRA Unittest', 'environment': None, 'fixVersions': [], 'description': 'se cayó todo..', 'customfield_10201': None, 'created': '2017-09-20T14:51:58.598+0000', 'versions': [], 'timetracking': {}, 'watches': {'self': 'http://192.168.10.101/rest/api/2/issue/PU-3/watchers', 'watchCount': 0, 'isWatching': False}, 'progress': {'total': 0, 'progress': 0}, 'creator': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}, 'resolutiondate': None, 'issuelinks': [], 'customfield_10200': None, 'aggregateprogress': {'total': 0, 'progress': 0}, 'priority': {'id': '3', 'self': 'http://192.168.10.101/rest/api/2/priority/3', 'name': 'Medium', 'iconUrl': 'http://192.168.10.101/images/icons/priorities/medium.svg'}, 'updated': '2017-09-20T14:51:58.598+0000', 'status': {'id': '10003', 'self': 'http://192.168.10.101/rest/api/2/status/10003', 'iconUrl': 'http://192.168.10.101/', 'description': '', 'statusCategory': {'id': 2, 'self': 'http://192.168.10.101/rest/api/2/statuscategory/2', 'colorName': 'blue-gray', 'key': 'new', 'name': 'Por hacer'}, 'name': 'Por hacer'}, 'assignee': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}, 'customfield_10006': None, 'resolution': None, 'customfield_10202': None, 'comment': {'total': 0, 'maxResults': 0, 'startAt': 0, 'comments': []}, 'components': [], 'issuetype': {'id': '10002', 'self': 'http://192.168.10.101/rest/api/2/issuetype/10002', 'subtask': False, 'iconUrl': 'http://192.168.10.101/secure/viewavatar?size=xsmall&avatarId=10318&avatarType=issuetype', 'description': 'Una tarea que necesita ser realizada.', 'name': 'Tarea', 'avatarId': 10318}, 'timeoriginalestimate': None, 'workratio': -1, 'subtasks': [], 'customfield_10005': '0|i0045z:', 'labels': [], 'duedate': None, 'timespent': None, 'reporter': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}, 'aggregatetimespent': None, 'customfield_10000': None, 'worklog': {'total': 0, 'maxResults': 20, 'startAt': 0, 'worklogs': []}, 'attachment': [], 'project': {'id': '10400', 'self': 'http://192.168.10.101/rest/api/2/project/10400', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/projectavatar?avatarId=10324', '32x32': 'http://192.168.10.101/secure/projectavatar?size=medium&avatarId=10324', '16x16': 'http://192.168.10.101/secure/projectavatar?size=xsmall&avatarId=10324', '24x24': 'http://192.168.10.101/secure/projectavatar?size=small&avatarId=10324'}, 'key': 'PU', 'name': 'Project Unicorn'}, 'timeestimate': None, 'aggregatetimeoriginalestimate': None, 'customfield_10001': None, 'customfield_10100': None, 'lastViewed': None, 'votes': {'self': 'http://192.168.10.101/rest/api/2/issue/PU-3/votes', 'votes': 0, 'hasVoted': False}}}, 'timestamp': 1505919118656, 'webhookEvent': 'jira:issue_created', 'issue_event_type_name': 'issue_created', 'user': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}}

    def _data(self):
        return {'description' : 'mm', 'reporter' : 'lrubiano', 'assignee' : 'lrubiano', 'issuetype' : '10002',
                'summary' : 'mm'}

    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        self.assertIsInstance(self.source_controller._connection_object, JiraConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.SugarCRM)
        self.assertIsInstance(self.source_controller._connection, JiraClient)

    def test_get_projects(self):
        """Testea que traiga todos los proyectos"""
        result = self.source_controller.get_projects()
        self.assertIsInstance(result, list)

    def test_get_mapping_fields(self):
        """Comprueba que el resultado sea una instancia de Mapfields
        """
        result = self.source_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_do_webhook_process(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.
        """
        result = self.source_controller.do_webhook_process(self.hook)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)

    def test_test_connection(self):
        """Comprueba que la conexión este establecida"""
        result = self.source_controller.test_connection()
        self.assertTrue(result)

    def test_create_issue(self):
        """Comprueba que se cree un issue, al final borra el issue de la aplicación"""
        result_create = self.target_controller.create_issue(os.environ.get('TEST_JIRA_PROJECT'), self._data())
        try:
            result_view = self.target_controller.view_issue(result_create)
        except:
            result_view =''
        self.assertEqual(result_create,result_view)
        self.target_controller.delete_issue(result_create)

    def test_create_webhook(self):
        """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
        webhook de la aplicación"""
        result = self.source_controller.create_webhook()
        count_webhook = Webhook.objects.filter(plug=self.plug_source).count()
        webhook = Webhook.objects.last()
        _id_webhook = int(webhook.generated_id)
        self.source_controller.delete_webhook(_id_webhook)
        self.assertTrue(result)
        self.assertEqual(count_webhook, 1)

    def test_get_key(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.
        """
        result = self.source_controller.get_key(os.environ.get('TEST_JIRA_PROJECT'))
        self.assertTrue(result)

    def test_get_header(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.
        """
        result = self.source_controller._get_header()
        self.assertIsInstance(result, dict)
        self.assertIn('Accept', result)
        self.assertIn('Authorization', result)

    def test_get_users(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.
        """
        result = self.source_controller.get_users()
        self.assertNotEqual(result, [])
        self.assertIn('id', result[0])
        self.assertIn('name', result[0])

    def test_get_meta(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.
        """
        result = self.target_controller.get_meta()
        self.assertIsInstance(result, list)

    def test_get_target_fields(self):
        """
        Comprueba que traiga los fields esperados
        """
        result = self.target_controller.get_meta()
        self.assertEqual(result, self.target_controller.get_meta())

    def test_get_action_specification_options(self):
        """
        Testea que traiga los proyectos creados en la aplicación, funciona mediante la variable
        TEST_JIRA_PROJECT, el cual debe ser un ID de un proyecto real creado en la aplicación
        """
        action_specification_id = self.specification_target.id
        result = self.target_controller.get_action_specification_options(action_specification_id)
        _project = None
        for i in result:
            if i["id"] == os.environ.get("TEST_JIRA_PROJECT"):
                _project = i["id"]
        self.assertIsInstance(result, tuple)
        self.assertEqual(_project, os.environ.get("TEST_JIRA_PROJECT"))

    def test_view_issue(self):
        """
        Testea que traiga los parámetros de un issue, al final borra de la aplicación el issue
        """
        result_create = self.target_controller.create_issue(os.environ.get('TEST_JIRA_PROJECT'), self._data())
        result_view = self.target_controller.view_issue(result_create)
        self.assertEqual(result_create,result_view)
        self.target_controller.delete_issue(result_create)

    def test_delete_issue(self):
        """
        Comprueba que borre un issue de la aplicación
        """
        result_create = self.target_controller.create_issue(os.environ.get('TEST_JIRA_PROJECT'), self._data())
        try:
            self.target_controller.delete_issue(result_create)
            _delete = True
        except:
            _delete = False
        self.assertTrue(_delete)

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, issue=self.hook['issue'])
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
        count_data = len(self.hook['issue']['fields'])
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source, issue=self.hook['issue'])
        count_store = StoredData.objects.filter(connection=self.connection_source, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        self.assertEqual(count_data, count_store)
        data = str(self.hook['issue']['fields'])
        self.assertEqual(history.identifier, str({'name': 'key', 'value': self.hook['issue']['key']}))

    def test_send_stored_data(self):
        """Simula un dato de entrada (self._data), y verifica que retorne una lista de acuerdo a los parámetros establecidos
        """
        data_list = [OrderedDict(self._data())]
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
        result_view = self.target_controller.view_issue(result[-1]['identifier'])
        self.assertEqual(result_view, result[-1]['identifier'])
        self.target_controller.delete_issue(result[-1]['identifier'])
