import os
import re
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.email import GmailController
from apps.gp.models import Connection, GmailConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Webhook, StoredData, Gear, GearMap, GearMapData
from apps.history.models import DownloadHistory, SendHistory

class GmailControllerTestCases(TestCase):
    """
        TEST_GMAIL_CREDENTIALS_JSON : String: Credentials
    """

    fixtures = ["gp_base22.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.Batchbook.value
        }
        cls.source_connection = Connection.objects.create(**connection)

        _source_connection = {
            "connection": cls.source_connection,
            "name": "ConnectionTest Source",
            "credentials_json": os.environ.get("TEST_GMAIL_CREDENTIALS_JSON"),
        }
        cls.gmail_source_connection = GmailConnection.objects.create(**_source_connection)

        cls.target_connection = Connection.objects.create(**connection)

        _target_connection = {
            "connection": cls.target_connection,
            "name": "ConnectionTest Target",
            "credentials_json": os.environ.get("TEST_GMAIL_CREDENTIALS_JSON"),
        }
        cls.gmail_target_connection = GmailConnection.objects.create(**_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.Gmail.value, action_type="source",
                                           name="PENDIENTE", is_active=True)

        _gmail_source_plug = {
            "name": "PlugTest Source",
            "connection": cls.source_connection,
            "action": source_action,
            "plug_type": "source",
            "user": cls.user,
            "is_active": True
        }
        cls.source_plug = Plug.objects.create(**_gmail_source_plug)

        target_action = Action.objects.get(connector_id=ConnectorEnum.Gmail.value, action_type="target",
                                           name="PENDIENTE", is_active=True)

        _gmail_target_plug = {
            "name": "PlugTest Target",
            "connection": cls.target_connection,
            "action": target_action,
            "plug_type": "target",
            "user": cls.user,
            "is_active": True
        }
        cls.target_plug = Plug.objects.create(**_gmail_target_plug)

        gear = {
            "name": "Gear 1",
            "user": cls.user,
            "source": cls.source_plug,
            "target": cls.target_plug,
            "is_active": True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)


    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self.source_controller = GmailController(self.source_plug.connection.related_connection,
                                                          self.source_plug)
        self.target_controller = GmailController(self.target_plug.connection.related_connection,
                                                          self.target_plug)

    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        self.assertIsInstance(self.source_controller._connection_object, GmailConnection)
        self.assertIsInstance(self.target_controller._connection_object, GmailConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)
        self.assertTrue(self.source_controller._credential)
        self.assertTrue(self.target_controller._credential)
        self.assertTrue(self.source_controller._service)
        self.assertTrue(self.target_controller._service)

    def test_test_connection(self):
        """
        Comprueba que la conexión sea valida
        """
        source_result = self.source_controller.test_connection()
        target_result = self.target_controller.test_connection()
        self.assertTrue(source_result)
        self.assertTrue(target_result)


    ## PENDIENTES

    def test_download_source_data(self):
        "Simula un dato de entrada y verifica que esté se cree en las tablas DownloadHistory y StoreData"
        self.source_controller.download_source_data(self.source_plug.connection.related_connection, self.source_plug)
        count_store = StoredData.objects.filter(connection=self.source_connection, plug=self.source_plug).count()
        count_history = DownloadHistory.objects.all().count()
        self.assertNotEqual(count_store, 0)
        self.assertNotEqual(count_history, 0)

    def test_download_to_store_data(self):
        """Verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.source_controller.download_to_stored_data(self.source_plug.connection.related_connection, self.source_plug)
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

    def test_get_target_fields(self):
        """Verifica los fields de un contacto"""
        result = self.target_controller.get_target_fields()
        self.assertEqual(result, self._get_fields())

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.target_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

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

    def test_send_target_data(self):
        """Verifica que se cree el registro ingresado en la tabla Sendstoredata, al final se borra
        el contacto de la aplicación"""
        _target = OrderedDict(self._target_fields)
        result = self.target_controller.send_target_data(source_data=self._source_data, target_fields=_target)
        count_history = SendHistory.objects.all().count()
        self.assertNotEqual(count_history, 0)
        self.target_controller._client.delete_contact(result[0])
