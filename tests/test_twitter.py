import os
from apps.gp.controllers.social import TwitterController
from apps.gp.controllers.database import MySQLController
from apps.gp.models import User, ConnectorEnum, Connection, Action, Plug, ActionSpecification, TwitterConnection, \
    PlugActionSpecification, Gear, MySQLConnection, GearMap, GearMapData, StoredData, SendHistory
from django.test import TestCase
from collections import OrderedDict


class TwitterControllerTestCases(TestCase):
    """Casos de prueba del controlador Twitter.

    Variables de entorno:
        TEST_MYSQL_SOURCE_HOST: String: Host del servidor..
        TEST_MYSQL_SOURCE_DATABASE String: Nombre de la base de datos.
        TEST_MYSQL_SOURCE_TABLE: String: Nombre de la tabla.
        TEST_MYSQL_SOURCE_PORT: String: Nùmero de puerto.
        TEST_MYSQL_SOURCE_CONNECTION_USER: String: Usuario.
        TEST_MYSQL_SOURCE_CONNECTION_PASSWORD: String: Contraseña.

        TEST_TWITTER_TOKEN: Token de la aplicación.
        TEST_TWITTER_TOKEN_SECRET String: Secret de la aplicación.

    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
        cls.user = User.objects.create(username='test', email='lyrubiano5@gmail.com', password='Prueba#2017')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Twitter.value
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

        twitter_connection1 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'token': os.environ.get('TEST_TWITTER_TOKEN'),
            'token_secret': os.environ.get('TEST_TWITTER_TOKEN_SECRET')
        }
        cls.twitter_connection1 = TwitterConnection.objects.create(**twitter_connection1)

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

        action_target = Action.objects.get(connector_id=ConnectorEnum.Twitter.value, action_type='target',
                                           name='post new tweet', is_active=True)

        twitter_plug_source = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**twitter_plug_source)

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

        map_data_1 = {'target_name': 'status', 'source_value': '%%name%%', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_1)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        # self.client = Client()
        self.source_controller = MySQLController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = TwitterController(self.plug_target.connection.related_connection, self.plug_target)

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.target_controller._connection_object, TwitterConnection)
        self.assertIsInstance(self.target_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.SugarCRM)

    def test_send_stored_data(self):
        """Guarda datos en StoredData y luego los envía la data mapeada al servidor CRM, luego comprueba de que
               el valor devuelto sea una lista además de comprobar que esté guardando registros en SendHistory.

        """
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
        entries = self.target_controller.send_target_data(source_data, target_fields, is_first=is_first)
        self.assertIsInstance(entries, list)

        for object_id in entries:
            count = SendHistory.objects.filter(identifier=object_id).count()
            self.assertGreater(count, 0)
