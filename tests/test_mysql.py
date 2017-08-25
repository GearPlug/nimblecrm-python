from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, ConnectorEnum, MySQLConnection, Plug, Action
from apps.gp.controllers.database import MySQLController


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
            'database': 'DatabaseTest',
            'table': 'TableTest',
            'port': '3306',
            'connection_user': 'UserTest',
            'connection_password': 'PasswordTest',
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

    def setUp(self):
        self.client = Client()

    def test_controller(self):
        controller = MySQLController()
        controller.create_connection(self.plug.connection.related_connection, self.plug)
        # print(controller._connection, controller._database, controller._table, controller._cursor)
        self.assertIsNone(controller._connection)
        self.assertIsInstance((controller._database, None))
        self.assertIsInstance((controller._table, None))
        self.assertIsNone(controller._cursor)

        # self.client.get()