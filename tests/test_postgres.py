import os
from django.test import TestCase
from django.contrib.auth.models import User
from apps.gp.models import Connection, PostgreSQLConnection, Plug, Action, StoredData, PlugActionSpecification, \
    ActionSpecification, Gear, GearMap, GearMapData
from apps.gp.controllers.database import PostgreSQLController
from apps.gp.enum import ConnectorEnum
from collections import OrderedDict


class PostgresControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.PostgreSQL.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        postgres_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'host': os.environ.get('TEST_POSTGRESQL_SOURCE_HOST'),
            'database': os.environ.get('TEST_POSTGRESQL_SOURCE_DATABASE'),
            'schema': os.environ.get('TEST_POSTGRESQL_SOURCE_SCHEMA'),
            'table': os.environ.get('TEST_POSTGRESQL_SOURCE_TABLE'),
            'port': os.environ.get('TEST_POSTGRESQL_SOURCE_PORT'),
            'connection_user': os.environ.get('TEST_POSTGRESQL_SOURCE_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_POSTGRESQL_SOURCE_CONNECTION_PASSWORD')
        }
        cls.postgres_connection1 = PostgreSQLConnection.objects.create(**postgres_connection1)

        cls.connection_target = Connection.objects.create(**connection)

        postgres_connection2 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'host': os.environ.get('TEST_POSTGRESQL_TARGET_HOST'),
            'database': os.environ.get('TEST_POSTGRESQL_TARGET_DATABASE'),
            'schema': os.environ.get('TEST_POSTGRESQL_TARGET_SCHEMA'),
            'table': os.environ.get('TEST_POSTGRESQL_TARGET_TABLE'),
            'port': os.environ.get('TEST_POSTGRESQL_TARGET_PORT'),
            'connection_user': os.environ.get('TEST_POSTGRESQL_TARGET_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_POSTGRESQL_TARGET_CONNECTION_PASSWORD')
        }
        cls.postgres_connection2 = PostgreSQLConnection.objects.create(**postgres_connection2)

        action_source = Action.objects.get(connector_id=ConnectorEnum.PostgreSQL.value, action_type='source',
                                           name='get row', is_active=True)

        postgres_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**postgres_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.PostgreSQL.value, action_type='target',
                                           name='create row', is_active=True)

        postgres_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**postgres_plug_target)

        specification1 = ActionSpecification.objects.get(action=action_source, name='unique')
        specification2 = ActionSpecification.objects.get(action=action_source, name='order by')

        action_specification1 = {
            'plug': cls.plug_source,
            'action_specification': specification1,
            'value': 'id'
        }
        PlugActionSpecification.objects.create(**action_specification1)

        action_specification2 = {
            'plug': cls.plug_source,
            'action_specification': specification2,
            'value': 'id'
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

        map_data_1 = {'target_name': 'old_id', 'source_value': '%%id%%', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'name', 'source_value': '%%name%%', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)

    def setUp(self):
        # self.client = Client()
        self.source_controller = PostgreSQLController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = PostgreSQLController(self.plug_target.connection.related_connection, self.plug_target)

    def test_controller(self):
        self.assertIsInstance(self.source_controller._connection_object, PostgreSQLConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.source_controller._connector, ConnectorEnum.MySQL)

    def test_describe_table(self):
        result = self.source_controller.describe_table()
        self.assertTrue(result)

    def test_select_all(self):
        # Error 2
        result = self.source_controller.select_all()
        self.assertTrue(result)

    def test_download_to_stored_data(self):
        connection = self.source_controller._connection_object.connection
        plug = self.source_controller._plug

        result1 = self.source_controller.download_source_data()
        self.assertTrue(result1)
        count1 = StoredData.objects.filter(connection=connection, plug=plug).count()

        result2 = self.source_controller.download_source_data()
        self.assertFalse(result2)
        count2 = StoredData.objects.filter(connection=connection, plug=plug).count()

        self.assertEqual(count1, count2)

    def test_get_action_specification_options(self):
        # TODO: CAMBIAR A QUERY CON NAME
        self.assertTrue(isinstance(self.source_controller.get_action_specification_options(1), tuple))
        self.assertTrue(isinstance(self.source_controller.get_action_specification_options(42), tuple))

    def test_send_stored_data(self):
        result1 = self.source_controller.download_source_data()
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
