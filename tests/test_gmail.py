import os
import re
import json
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.email import GmailController
from apps.gp.models import Connection, GmailConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Webhook, StoredData, Gear, GearMap, GearMapData
from apps.history.models import DownloadHistory, SendHistory
import base64

class GmailControllerTestCases(TestCase):
    """
        TEST_GMAIL_CREDENTIALS_JSON : String: Credentials
        TEST_GMAIL_EMAIL : String: Credentials
    """

    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.Batchbook.value
        }
        cls.source_connection = Connection.objects.create(**connection)

        _credentials = json.loads(os.environ.get('TEST_GMAIL_CREDENTIALS_JSON'))

        _source_connection = {
            "connection": cls.source_connection,
            "name": "ConnectionTest Source",
            "credentials_json": _credentials,
        }
        cls.gmail_source_connection = GmailConnection.objects.create(**_source_connection)

        cls.target_connection = Connection.objects.create(**connection)

        _target_connection = {
            "connection": cls.target_connection,
            "name": "ConnectionTest Target",
            "credentials_json":_credentials,
        }
        cls.gmail_target_connection = GmailConnection.objects.create(**_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.Gmail.value, action_type="source",
                                           name="new email", is_active=True)

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
                                           name="send email", is_active=True)

        _gmail_target_plug = {
            "name": "PlugTest Target",
            "connection": cls.target_connection,
            "action": target_action,
            "plug_type": "target",
            "user": cls.user,
            "is_active": True
        }
        cls.target_plug = Plug.objects.create(**_gmail_target_plug)

        cls.source_specification = ActionSpecification.objects.get(action=source_action,
                                                                   name='email')

        cls.target_specification = ActionSpecification.objects.get(action=target_action,
                                                                   name='email')

        _dict_source_specification = {
            'plug': cls.source_plug,
            'action_specification': cls.source_specification,
            'value': os.environ.get('TEST_GMAIL_EMAIL')
        }
        PlugActionSpecification.objects.create(**_dict_source_specification)

        _dict_target_specification = {
            'plug': cls.target_plug,
            'action_specification': cls.target_specification,
            'value': os.environ.get('TEST_GMAIL_EMAIL')
        }
        PlugActionSpecification.objects.create(**_dict_target_specification)

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

    def _get_email(self):
        return {'message': {'publish_time': '2017-12-07T14:49:59.798Z', 'publishTime': '2017-12-07T14:49:59.798Z', 'attributes': {}, 'message_id': '179953654612940', 'messageId': '179953654612940', 'data': 'eyJlbWFpbEFkZHJlc3MiOiJncnBsdWd0ZXN0MkBnbWFpbC5jb20iLCJoaXN0b3J5SWQiOjIzNjB9'}, 'subscription': 'projects/gearplugtest2/subscriptions/test'}

    # def test_controller(self):
    #     """
    #     Comprueba que los atributos del controlador esten instanciados
    #     """
    #     self.assertIsInstance(self.source_controller._connection_object, GmailConnection)
    #     self.assertIsInstance(self.target_controller._connection_object, GmailConnection)
    #     self.assertIsInstance(self.source_controller._plug, Plug)
    #     self.assertIsInstance(self.target_controller._plug, Plug)
    #     self.assertTrue(self.source_controller._credential)
    #     self.assertTrue(self.target_controller._credential)
    #     self.assertTrue(self.source_controller._service)
    #     self.assertTrue(self.target_controller._service)
    #
    # def test_test_connection(self):
    #     """
    #     Comprueba que la conexión sea valida
    #     """
    #     source_result = self.source_controller.test_connection()
    #     target_result = self.target_controller.test_connection()
    #     self.assertTrue(source_result)
    #     self.assertTrue(target_result)

    # def test_create_webhook(self):
    #     """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
    #     webhook de la aplicación"""
    #     self.source_controller.create_webhook()
    #     count_webhook = Webhook.objects.filter(plug=self.source_plug).count()
    #     self.assertEqual(count_webhook, 1)

    # def test_get_profile(self):
    #     result = self.source_controller.get_profile()
    #     self.assertIn('emailAddress', result)
    #     self.assertEqual(result['emailAddress'], os.environ.get('TEST_GMAIL_EMAIL'))

    # def test_get_action_specification_options(self):
    #     action_specification_id = self.source_specification.id
    #     result = self.source_controller.get_action_specification_options(action_specification_id)
    #     self.assertIsInstance(result, tuple)
    #     self.assertEqual(result[0]['id'], os.environ.get('TEST_GMAIL_EMAIL'))

    def test_get_history(self):
        encoded_message_data = base64.urlsafe_b64decode(self._get_email()['message']['data'].encode('ASCII'))
        decoded_message_data = json.loads(encoded_message_data.decode('utf-8'))
        history_id = decoded_message_data['historyId']
        result = self.source_controller.get_history(history_id)
        self.assertIn('historyId', result)

    # def test_get_message(self):
    #     message_id = self._get_email()['message']['messageId']
    #     result = self.source_controller.get_message(message_id=message_id)
    #     print("result", result)

    # ## PENDIENTES
    #
    # def test_download_source_data(self):
    #     "Simula un dato de entrada y verifica que esté se cree en las tablas DownloadHistory y StoreData"
    #     self.source_controller.download_source_data(self.source_plug.connection.related_connection, self.source_plug)
    #     count_store = StoredData.objects.filter(connection=self.source_connection, plug=self.source_plug).count()
    #     count_history = DownloadHistory.objects.all().count()
    #     self.assertNotEqual(count_store, 0)
    #     self.assertNotEqual(count_history, 0)
    #
    # def test_download_to_store_data(self):
    #     """Verifica que retorne una lista de acuerdo a:
    #     {'downloaded_data':[
    #         {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
    #          "is_stored": True | False},
    #          "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
    #         {...}, {...},
    #      "last_source_record":(%last_order_by_value)},}
    #     """
    #     result = self.source_controller.download_to_stored_data(self.source_plug.connection.related_connection, self.source_plug)
    #     self.assertIn('downloaded_data', result)
    #     self.assertIsInstance(result['downloaded_data'], list)
    #     self.assertIsInstance(result['downloaded_data'][-1], dict)
    #     self.assertIn('identifier', result['downloaded_data'][-1])
    #     self.assertIsInstance(result['downloaded_data'][-1]['identifier'], dict)
    #     self.assertIn('name', result['downloaded_data'][-1]['identifier'])
    #     self.assertIn('value', result['downloaded_data'][-1]['identifier'])
    #     self.assertIsInstance(result['downloaded_data'][-1], dict)
    #     self.assertIn('raw', result['downloaded_data'][-1])
    #     self.assertIsInstance(result['downloaded_data'][-1]['raw'], dict)
    #     self.assertIn('is_stored', result['downloaded_data'][-1])
    #     self.assertIsInstance(result['downloaded_data'][-1]['is_stored'], bool)
    #     self.assertIn('last_source_record', result)
    #     self.assertIsNotNone(result['last_source_record'])
    #
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
    #
    # def test_send_stored_data(self):
    #     """ Verifica que se cree un contacto y que el métod send_store_data retorne una lista de acuerdo a:
    #             {'data': {(%dict del metodo 'get_dict_with_source_data')},
    #              'response': (%mensaje del resultado),
    #              'sent': True|False,
    #              'identifier': (%identificador del dato enviado. Ej: ID.)
    #             }
    #             Al final se borra el contacto de la aplicación.
    #             """
    #     data_list = [OrderedDict(self._data)]
    #     result = self.target_controller.send_stored_data(data_list)
    #     self.assertIsInstance(result, list)
    #     self.assertIsInstance(result[-1], dict)
    #     self.assertIn('data', result[-1])
    #     self.assertIn('response', result[-1])
    #     self.assertIn('sent', result[-1])
    #     self.assertIn('identifier', result[-1])
    #     self.assertIsInstance(result[-1]['data'], dict)
    #     self.assertIsInstance(result[-1]['response'], dict)
    #     self.assertIsInstance(result[-1]['sent'], bool)
    #     self.assertEqual(result[-1]['data'], dict(data_list[0]))
    #     result_view = self.target_controller._client.get_contact(contact_id=result[-1]['identifier'])
    #     self.assertEqual(result_view['id'], result[-1]['identifier'])
    #     self.target_controller._client.delete_contact(contact_id=result[-1]['identifier'])
    #
    # def test_send_target_data(self):
    #     """Verifica que se cree el registro ingresado en la tabla Sendstoredata, al final se borra
    #     el contacto de la aplicación"""
    #     _target = OrderedDict(self._target_fields)
    #     result = self.target_controller.send_target_data(source_data=self._source_data, target_fields=_target)
    #     count_history = SendHistory.objects.all().count()
    #     self.assertNotEqual(count_history, 0)
    #     self.target_controller._client.delete_contact(result[0])
