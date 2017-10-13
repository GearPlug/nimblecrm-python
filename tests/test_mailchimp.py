import os
from collections import OrderedDict
from apps.gp.models import Connection, MailChimpConnection, Plug, Action, PlugActionSpecification, ActionSpecification, \
    Gear, GearMap, GearMapData, StoredData, MySQLConnection
from apps.gp.controllers.database import MySQLController
from apps.history.models import DownloadHistory, SendHistory
from apps.gp.controllers.email_marketing import MailChimpController
from django.contrib.auth.models import User
from django.test import TestCase
from apps.gp.enum import ConnectorEnum
from mailchimp.client import Client as MailchimpClient
from apps.gp.map import MapField


class MailchimpControllerTestCases(TestCase):
    """Casos de prueba del controlador SugarCRM.

            Variables de entorno:
                TEST_MAILCHIMP_TOKEN: String: Token de acceso.
                TEST_MAILCHIMP_LIST: String: Lista de contactos.
                TEST_MYSQL_SOURCE_HOST: String: Host del servidor..
                TEST_MYSQL_SOURCE_DATABASE String: Nombre de la base de datos.
                TEST_MYSQL_SOURCE_TABLE: String: Nombre de la tabla.
                TEST_MYSQL_SOURCE_PORT: String: Nùmero de puerto.
                TEST_MYSQL_SOURCE_CONNECTION_USER: String: Usuario.
                TEST_MYSQL_SOURCE_CONNECTION_PASSWORD: String: Contraseña.

        """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
        cls.user = User.objects.create(username='lyrubiano', email='lyrubiano5@gmail.com',
                                       password='Prueba#2017')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.MailChimp.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        mysql_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'host': os.environ.get('TEST_MYSQL_SOURCE_HOST'),
            'database': os.environ.get('TEST_MYSQL_SOURCE_DATABASE'),
            'table': os.environ.get('TEST_MYSQL_SOURCE_TABLE'),
            'port': os.environ.get('TEST_MYSQL_SOURCE_PORT'),
            'connection_user': os.environ.get('TEST_MYSQL_SOURCE_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_MYSQL_SOURCE_CONNECTION_PASSWORD')
        }
        cls.mysql_connection1 = MySQLConnection.objects.create(**mysql_connection1)

        cls.connection_target = Connection.objects.create(**connection)

        cls._token = os.environ.get('TEST_MAILCHIMP_TOKEN')

        mailchimp_connection1 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'token': cls._token,
        }
        cls.mailchimp_connection_target = MailChimpConnection.objects.create(**mailchimp_connection1)

        action_source = Action.objects.get(connector_id=ConnectorEnum.MySQL.value, action_type='source', name='get row',
                                           is_active=True)

        mysql_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**mysql_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.MailChimp.value, action_type='target',
                                           name='subscribe', is_active=True)

        mailchimp_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_target = Plug.objects.create(**mailchimp_plug_target)

        specification1 = ActionSpecification.objects.get(action=action_source, name='unique')
        specification2 = ActionSpecification.objects.get(action=action_source, name='order by')
        cls.specification3 = ActionSpecification.objects.get(action=action_target, name='list')

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

        actionspecification_target = {
            'plug': cls.plug_target,
            'action_specification': cls.specification3,
            'value': os.environ.get('TEST_MAILCHIMP_LIST')
        }
        PlugActionSpecification.objects.create(**actionspecification_target)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_1 = {'target_name': 'email_address', 'source_value': 'mferrer@gmail.com', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'FNAME', 'source_value': '%%name%%', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        self.controller_source = MySQLController(self.plug_source.connection.related_connection, self.plug_source)
        self.controller_target = MailChimpController(self.plug_target.connection.related_connection, self.plug_target)

        self._client = MailchimpClient(access_token=self._token)

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.controller_target._connection_object, MailChimpConnection)
        self.assertIsInstance(self.controller_target._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.SugarCRM)
        self.assertIsInstance(self.controller_target._client, MailchimpClient)

    def _get_fields(self):
        return [
            {"name": "email_address", "required": True, "type": "varchar", "label": "email"},
            {"name": "FNAME", "required": False, "type": "varchar", "label": "First Name"},
            {"name": "LNAME", "required": False, "type": "varchar", "label": "Last Name"},
        ]

    def test_test_connection(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

                """
        result = self.controller_target.test_connection()
        self.assertTrue(result)

    def test_get_target_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_target.get_target_fields()
        self.assertEqual(result, self._get_fields())

    def test_get_mapping_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_target.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_action_specification_options(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        action_specification_id = self.specification3.id
        result = self.controller_target.get_action_specification_options(action_specification_id)
        _list = tuple({'id': c['id'], 'name': c['name']} for c in self._client.get_lists()['lists'])
        self.assertIsInstance(result, tuple)
        self.assertEqual(result, _list)

    def test_send_stored_data(self):
        """Guarda datos en StoredData y luego los envía la data mapeada al servidor CRM, luego comprueba de que
                el valor devuelto sea una lista además de comprobar que esté guardando registros en SendHistory.

        """
        result1 = self.controller_source.download_source_data()
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
        entries = self.controller_target.send_target_data(source_data, target_fields, is_first=is_first)
        self.assertIsInstance(entries, list)

        for object_id in entries:
            count = SendHistory.objects.filter(identifier=object_id).count()
            self.assertGreater(count, 0)
