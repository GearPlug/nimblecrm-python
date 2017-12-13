import os
import re
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.email_marketing import GetResponseController
from apps.gp.models import Connection, GetResponseConnection, MySQLConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Webhook, StoredData, Gear, GearMap, GearMapData
from apps.history.models import DownloadHistory, SendHistory
from getresponse.client import GetResponse


class GetResponseControllerTestCases(TestCase):
    """
        TEST_GET_RESPONSE_API_KEY : String: Api key
        TEST_GET_RESPONSE_CAMPAIGN: String ID Campaign

        # Credenciales para el source

        TEST_GET_RESPONSE_SOURCE_MYSQL_HOST: String
        TEST_GET_RESPONSE_SOURCE_MYSQL_DATABASE: String
        TEST_GET_RESPONSE_SOURCE_MYSQL_TABLE: String
        TEST_GET_RESPONSE_SOURCE_MYSQL_PORT: String
        TEST_GET_RESPONSE_SOURCE_MYSQL_CONNECTION_USER: String
        TEST_GET_RESPONSE_SOURCE_MYSQL_CONNECTION_PASSWORD: String
    """
    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.GetResponse.value
        }
        cls.source_connection = Connection.objects.create(**connection)

        _source_mysql_connection = {
            'connection': cls.source_connection,
            'name': 'ConnectionTest Source',
            'host': os.environ.get('TEST_GET_RESPONSE_SOURCE_MYSQL_HOST'),
            'database': os.environ.get('TEST_GET_RESPONSE_SOURCE_MYSQL_DATABASE'),
            'table': os.environ.get('TEST_GET_RESPONSE_SOURCE_MYSQL_TABLE'),
            'port': os.environ.get('TEST_GET_RESPONSE_SOURCE_MYSQL_PORT'),
            'connection_user': os.environ.get('TEST_GET_RESPONSE_SOURCE_MYSQL_CONNECTION_USER'),
            'connection_password': os.environ.get('TEST_GET_RESPONSE_SOURCE_MYSQL_CONNECTION_PASSWORD')
        }
        cls.get_response_source_connection = MySQLConnection.objects.create(**_source_mysql_connection)

        cls.target_connection = Connection.objects.create(**connection)

        _target_connection = {
            "connection": cls.target_connection,
            "name": "ConnectionTest Target",
            "api_key": os.environ.get("TEST_GET_RESPONSE_API_KEY"),
        }
        cls.get_response_target_connection = GetResponseConnection.objects.create(**_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.MySQL.value, action_type="source",
                                           name="get row", is_active=True)

        _mysql_source_plug = {
            "name": "PlugTest Source",
            "connection": cls.source_connection,
            "action": source_action,
            "plug_type": "source",
            "user": cls.user,
            "is_active": True
        }

        cls.source_plug = Plug.objects.create(**_mysql_source_plug)

        _list_target_actions = ['subscribe', 'Unsubscribe']
        cls._list_target_plugs = []

        for action in _list_target_actions:

            target_action = Action.objects.get(connector_id=ConnectorEnum.GetResponse.value, action_type="target",
                                               name=action, is_active=True)

            _get_response_target_plug = {
                "name": "PlugTest Target",
                "connection": cls.target_connection,
                "action": target_action,
                "plug_type": "target",
                "user": cls.user,
                "is_active": True
            }
            _target_plug = Plug.objects.create(**_get_response_target_plug)
            _target_specification = ActionSpecification.objects.get(action=target_action, name="campaign")
            _target_action_specification = {
                "plug": _target_plug,
                "action_specification": _target_specification,
                "value": os.environ.get('TEST_GET_RESPONSE_CAMPAIGN')
            }
            PlugActionSpecification.objects.create(**_target_action_specification)
            cls._list_target_plugs.append(
                {'action': action, 'plug': _target_plug, 'specification': _target_action_specification})

            for _plug in cls._list_target_plugs:
                _dict_gear = {
                    "name": "Gear",
                    "user": cls.user,
                    "source": cls.source_plug,
                    "target": _plug['plug'],
                    "is_active": True
                }
                _gear = Gear.objects.create(**_dict_gear)
                _gear_map = GearMap.objects.create(gear=_gear)
                _plug['gear'] = _gear
                _plug['gear map'] = _gear_map

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self._list_target_controllers = []
        for _plug in self._list_target_plugs:
            _target_controller = GetResponseController(_plug['plug'].connection.related_connection,
                                                       _plug['plug'])
            self._list_target_controllers.append(
                {'action': _plug['action'], 'controller': _target_controller, 'plug': _plug['plug'],
                 'specification': _plug['specification'], 'gear':_plug['gear'], 'gear_map':_plug['gear map']})

    def _get_datalist(self):
        return [OrderedDict([('email', 'grplugtest2@gmail.com')])]

    def _get_source(self):
        return [{'id': '11', 'data': {'id': '11', 'email': 'grplugtest2@gmail.com'}}]

    def _get_target(self):
        return OrderedDict(
            [('3jsPx', ''), ('3jsJa', ''), ('3jslm', ''), ('3jsjb', ''), ('3js0X', ''), ('3jsCo', ''), ('3jsmH', ''),
             ('3jstq', ''), ('3jskE', ''), ('3js9O', ''), ('3jsOL', ''), ('3jsq0', ''), ('3jswn', ''), ('3js55', ''),
             ('3jsfy', ''), ('3js71', ''), ('email', '%%sender%%'), ('3jsGw', ''), ('3jsi7', ''), ('dayOfCycle', ''),
             ('ipAddress', ''), ('name', '')])


    # def test_controller(self):
    #     """
    #     Comprueba que los atributos del controlador esten instanciados
    #     """
    #     for _controller in self._list_target_controllers:
    #         self.assertIsInstance(_controller['controller']._connection_object, GetResponseConnection)
    #         self.assertIsInstance(_controller['plug'], Plug)
    #         self.assertIsInstance(_controller['controller']._client, GetResponse)
    #
    # def test_test_connection(self):
    #     """
    #     Comprueba que la conexión sea valida
    #     """
    #     for _controller in self._list_target_controllers:
    #         result = _controller['controller'].test_connection()
    #         self.assertTrue(result)

    ##pendientes

    # def test_get_target_fields(self):
    #     """Verifica los fields de un contacto"""
    #     result = self.target_controller.get_target_fields()
    #     self.assertEqual(result, self._get_fields())
    #
    # def test_get_mapping_fields(self):
    #     """Testea que retorne los Mapping Fields de manera correcta"""
    #     result = self.target_controller.get_mapping_fields()
    #     self.assertIsInstance(result, list)
    #     self.assertIsInstance(result[0], MapField)

    ## pendientes

    def test_send_stored_data(self):
        """ Verifica que se cree un contacto y que el métod send_store_data retorne una lista de acuerdo a:
                {'data': {(%dict del metodo 'get_dict_with_source_data')},
                 'response': (%mensaje del resultado),
                 'sent': True|False,
                 'identifier': (%identificador del dato enviado. Ej: ID.)
                }
                Al final se borra el contacto de la aplicación.
                """
        data_list = [OrderedDict(self._data)]
        result = self.target_controller.send_stored_data(data_list)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)
        self.assertIn('data', result[-1])
        self.assertIn('response', result[-1])
        self.assertIn('sent', result[-1])
        self.assertIn('identifier', result[-1])
        self.assertIsInstance(result[-1]['data'], dict)
        self.assertIsInstance(result[-1]['response'], dict)
        self.assertIsInstance(result[-1]['sent'], bool)
        self.assertEqual(result[-1]['data'], dict(data_list[0]))
        result_view = self.target_controller._client.get_contact(contact_id=result[-1]['identifier'])
        self.assertEqual(result_view['id'], result[-1]['identifier'])
        self.target_controller._client.delete_contact(contact_id=result[-1]['identifier'])

    # def test_send_target_data(self):
    #     """Verifica que se cree el registro ingresado en la tabla Sendstoredata, al final se borra
    #     el contacto de la aplicación"""
    #     _target = OrderedDict(self._target_fields)
    #     result = self.target_controller.send_target_data(source_data=self._source_data, target_fields=_target)
    #     count_history = SendHistory.objects.all().count()
    #     self.assertNotEqual(count_history, 0)
    #     self.target_controller._client.delete_contact(result[0])
    #

