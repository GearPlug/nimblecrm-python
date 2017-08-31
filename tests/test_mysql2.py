from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, ConnectorEnum, MySQLConnection, Plug, Action, StoredData, PlugActionSpecification, ActionSpecification
from apps.gp.controllers.database import MySQLController
from MySQLdb.connections import Connection as MyConnection
from MySQLdb.cursors import Cursor as MyCursor
from apps.gp.enum import ConnectorEnum


class MysqlControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.MySQL.value
        }
        cls.connection = Connection.objects.create(**_dict)

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'host': 'localhost',
            'database': 'apiConnector-00',
            'table': 'gp_connection',
            'port': '3306',
            'connection_user': 'root',
            'connection_password': 'passwd',
        }
        cls.mysql_connection = MySQLConnection.objects.create(**_dict2)

        action = Action.objects.get(connector_id=ConnectorEnum.MySQL.value, action_type='source', name='get row',
                                    is_active=True)

        _dict3 = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug = Plug.objects.create(**_dict3)

        specification1 = ActionSpecification.objects.get(action=action, name='unique')
        specification2 = ActionSpecification.objects.get(action=action, name='order by')

        _dict4 = {
            'plug': cls.plug,
            'action_specification': specification1,
            'value': 'id'
        }
        PlugActionSpecification.objects.create(**_dict4)

        _dict5 = {
            'plug': cls.plug,
            'action_specification': specification2,
            'value': 'id'
        }
        PlugActionSpecification.objects.create(**_dict5)

    def setUp(self):
        # self.client = Client()
        self.controller = MySQLController(self.plug.connection.related_connection, self.plug)

    def test_controller(self):
        self.assertIsInstance(self.controller._connection_object, MySQLConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.MySQL)
        self.assertIsInstance(self.controller._connection, MyConnection)
        self.assertIsInstance(self.controller._cursor, MyCursor)

    def test_describe_table(self):
        result = self.controller.describe_table()
        self.assertTrue(result)

    def test_select_all(self):
        # Error 2
        result = self.controller.select_all()
        self.assertTrue(result)

    def test_download_to_stored_data(self):
        connection = self.controller._connection_object.connection
        plug = self.controller._plug

        result1 = self.controller.download_source_data()
        print(result1)
        self.assertTrue(result1)
        count1 = StoredData.objects.filter(connection=connection, plug=plug).count()
        print(count1)

        result2 = self.controller.download_source_data()
        print(result2)
        self.assertTrue(result2)
        count2 = StoredData.objects.filter(connection=connection, plug=plug).count()
        print(count2)

        self.assertEqual(count1, count2)
