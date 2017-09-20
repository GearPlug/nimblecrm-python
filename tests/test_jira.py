import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, JiraConnection, Plug, Action, ActionSpecification, PlugActionSpecification, \
    Gear, GearMap, StoredData, GearMapData
from apps.gp.controllers.project_management import JIRAController
from jira import JIRA as JiraClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class JiraControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.JIRA.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        jira_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'host': os.environ.get('TEST_JIRA_HOST'),
            'connection_user': os.environ.get('TEST_JIRA_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_JIRA_CONNECTION_PASSWORD')
        }
        cls.jira_connection1 = JiraConnection.objects.create(**jira_connection1)

        cls.connection_target = Connection.objects.create(**connection)

        jira_connection2 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'host': os.environ.get('TEST_JIRA_HOST'),
            'connection_user': os.environ.get('TEST_JIRA_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_JIRA_CONNECTION_PASSWORD')
        }
        cls.jira_connection2 = JiraConnection.objects.create(**jira_connection2)

        action_source = Action.objects.get(connector_id=ConnectorEnum.JIRA.value, action_type='source',
                                           name='new issue', is_active=True)

        jira_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_source = Plug.objects.create(**jira_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.JIRA.value, action_type='target',
                                           name='create issue', is_active=True)

        jira_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_target = Plug.objects.create(**jira_plug_target)

        specification1 = ActionSpecification.objects.get(action=action_source, name='project_id')
        specification2 = ActionSpecification.objects.get(action=action_target, name='project_id')

        action_specification1 = {
            'plug': cls.plug_source,
            'action_specification': specification1,
            'value': '10400'
        }
        PlugActionSpecification.objects.create(**action_specification1)

        action_specification2 = {
            'plug': cls.plug_target,
            'action_specification': specification2,
            'value': '10400'
        }
        PlugActionSpecification.objects.create(**action_specification2)

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
        # self.client = Client()
        self.source_controller = JIRAController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = JIRAController(self.plug_target.connection.related_connection, self.plug_target)

        self.hook = {'issue': {'id': '12507', 'self': 'http://192.168.10.101/rest/api/2/issue/12507', 'key': 'PU-3', 'fields': {'aggregatetimeestimate': None, 'summary': 'JIRA Unittest', 'environment': None, 'fixVersions': [], 'description': 'se cayó todo..', 'customfield_10201': None, 'created': '2017-09-20T14:51:58.598+0000', 'versions': [], 'timetracking': {}, 'watches': {'self': 'http://192.168.10.101/rest/api/2/issue/PU-3/watchers', 'watchCount': 0, 'isWatching': False}, 'progress': {'total': 0, 'progress': 0}, 'creator': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}, 'resolutiondate': None, 'issuelinks': [], 'customfield_10200': None, 'aggregateprogress': {'total': 0, 'progress': 0}, 'priority': {'id': '3', 'self': 'http://192.168.10.101/rest/api/2/priority/3', 'name': 'Medium', 'iconUrl': 'http://192.168.10.101/images/icons/priorities/medium.svg'}, 'updated': '2017-09-20T14:51:58.598+0000', 'status': {'id': '10003', 'self': 'http://192.168.10.101/rest/api/2/status/10003', 'iconUrl': 'http://192.168.10.101/', 'description': '', 'statusCategory': {'id': 2, 'self': 'http://192.168.10.101/rest/api/2/statuscategory/2', 'colorName': 'blue-gray', 'key': 'new', 'name': 'Por hacer'}, 'name': 'Por hacer'}, 'assignee': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}, 'customfield_10006': None, 'resolution': None, 'customfield_10202': None, 'comment': {'total': 0, 'maxResults': 0, 'startAt': 0, 'comments': []}, 'components': [], 'issuetype': {'id': '10002', 'self': 'http://192.168.10.101/rest/api/2/issuetype/10002', 'subtask': False, 'iconUrl': 'http://192.168.10.101/secure/viewavatar?size=xsmall&avatarId=10318&avatarType=issuetype', 'description': 'Una tarea que necesita ser realizada.', 'name': 'Tarea', 'avatarId': 10318}, 'timeoriginalestimate': None, 'workratio': -1, 'subtasks': [], 'customfield_10005': '0|i0045z:', 'labels': [], 'duedate': None, 'timespent': None, 'reporter': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}, 'aggregatetimespent': None, 'customfield_10000': None, 'worklog': {'total': 0, 'maxResults': 20, 'startAt': 0, 'worklogs': []}, 'attachment': [], 'project': {'id': '10400', 'self': 'http://192.168.10.101/rest/api/2/project/10400', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/projectavatar?avatarId=10324', '32x32': 'http://192.168.10.101/secure/projectavatar?size=medium&avatarId=10324', '16x16': 'http://192.168.10.101/secure/projectavatar?size=xsmall&avatarId=10324', '24x24': 'http://192.168.10.101/secure/projectavatar?size=small&avatarId=10324'}, 'key': 'PU', 'name': 'Project Unicorn'}, 'timeestimate': None, 'aggregatetimeoriginalestimate': None, 'customfield_10001': None, 'customfield_10100': None, 'lastViewed': None, 'votes': {'self': 'http://192.168.10.101/rest/api/2/issue/PU-3/votes', 'votes': 0, 'hasVoted': False}}}, 'timestamp': 1505919118656, 'webhookEvent': 'jira:issue_created', 'issue_event_type_name': 'issue_created', 'user': {'self': 'http://192.168.10.101/rest/api/2/user?username=damanrique', 'key': 'damanrique', 'timeZone': 'America/Lima', 'avatarUrls': {'48x48': 'http://192.168.10.101/secure/useravatar?ownerId=damanrique&avatarId=10503', '32x32': 'http://192.168.10.101/secure/useravatar?size=medium&ownerId=damanrique&avatarId=10503', '16x16': 'http://192.168.10.101/secure/useravatar?size=xsmall&ownerId=damanrique&avatarId=10503', '24x24': 'http://192.168.10.101/secure/useravatar?size=small&ownerId=damanrique&avatarId=10503'}, 'active': True, 'name': 'damanrique', 'emailAddress': 'damanrique@grplug.com', 'displayName': 'Diego Manrique'}}

    def test_controller(self):
        self.assertIsInstance(self.source_controller._connection_object, JiraConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.SugarCRM)
        self.assertIsInstance(self.source_controller._connection, JiraClient)

    def test_get_projects(self):
        result = self.source_controller.get_projects()
        self.assertIsInstance(result, list)

    def test_get_users(self):
        result = self.source_controller.get_users()
        self.assertNotEqual(result, [])

    def test_get_mapping_fields(self):
        result = self.source_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_do_webhook_process(self):
        result = self.source_controller.do_webhook_process(self.hook)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)

    def test_send_stored_data(self):
        result1 = self.source_controller.do_webhook_process(self.hook)
        self.assertIsNotNone(result1)
        query_params = {'connection': self.gear.source.connection, 'plug': self.gear.source}
        is_first = self.gear_map.last_sent_stored_data_id is None
        if not is_first:
            query_params['id__gt'] = self.gear.gear_map.last_sent_stored_data_id
        stored_data = StoredData.objects.filter(**query_params)
        target_fields = OrderedDict(
            (data.target_name, data.source_value) for data in GearMapData.objects.filter(gear_map=self.gear_map))
        source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}} for
                       item in stored_data.values_list('object_id').distinct()]
        entries = self.target_controller.send_stored_data(source_data, target_fields, is_first=is_first)
        self.assertIsInstance(entries, list)
