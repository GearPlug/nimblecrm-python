from django.test import TestCase
import sqlite3
import sys, types
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
            'token': 'localhost',
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

        # print(type(connection))
        # print(plug)

        result1 = self.controller.download_source_data()
        self.assertTrue(result1)
        count1 = StoredData.objects.filter(connection=connection, plug=plug).count()

        result2 = self.controller.download_source_data()
        self.assertTrue(result2)
        count2 = StoredData.objects.filter(connection=connection, plug=plug).count()

        self.assertEqual(count1, count2)

    def test_insert(self):
        item = {"LastName": "Perez", "FirstName": "Pedro", "Address": "Cll 123", "City": "Bogota"}
        sql=self.controller._get_insert_statement(item)
        self.assertRaises(Exception,self.valid_query(sql.replace('table2', "Persons")))

    def valid_query(self,sql):
        create = "CREATE TABLE Persons ( " \
                "PersonID int, " \
                "LastName varchar(255), " \
                "FirstName varchar(255), " \
                "Address varchar(255), " \
                "City varchar(255));"
        temp_db = sqlite3.connect(":memory:")
        temp_db.execute(create)
        try:
            temp_db.execute(sql)
        except Exception as e:
            print(e)
            raise

    def test_get_action_specification_options(self):
        self.assertTrue(isinstance(self.controller.get_action_specification_options(1), tuple))
        self.assertTrue(isinstance(self.controller.get_action_specification_options(42), tuple))

