import os
import re
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.models import Connection, ActiveCampaignConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Webhook, StoredData, Gear, GearMap, GearMapData, TypeFormConnection
from apps.history.models import DownloadHistory
from apps.gp.controllers.lead import TypeFormController

class TypeFormControllerTestCases(TestCase):
    """
        TEST_TYPEFORM_API_KEY : String: Api Key de la aplicación
        TEST_TYPEFORM_FORM : String: Api ID de un formulario existente en la aplicacion
    """
    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        _dict_connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.TypeForm.value
        }
        cls.connection = Connection.objects.create(**_dict_connection)

        _dict_typeform_connection = {
            'connection':cls.connection,
            'name':'ConnectionTest',
            'api_key':os.environ.get('TEST_TYPEFORM_API_KEY')
        }

        cls.typeform_connection = TypeFormConnection.objects.create(**_dict_typeform_connection)

        action = Action.objects.get(connector_id=ConnectorEnum.TypeForm.value, action_type="source",
                                           name="new answer", is_active=True)

        _dict_typeform_plug = {
            "name": "PlugTest Source",
            "connection": cls.connection,
            "action": action,
            "plug_type": "source",
            "user": cls.user,
            "is_active": True
        }
        cls.plug = Plug.objects.create(**_dict_typeform_plug)

        cls.specification = ActionSpecification.objects.get(action=action, name="form")

        _action_specification = {
            "plug": cls.plug,
            "action_specification": cls.specification,
            "value": os.environ.get("TEST_TYPEFORM_FORM")
        }

        PlugActionSpecification.objects.create(**_action_specification)

        gear = {
            "name": "Gear 1",
            "user": cls.user,
            "source": cls.plug,
            "target": cls.plug,
            "is_active": True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self.controller= TypeFormController(self.plug.connection.related_connection,self.plug)

        self.hook = {"event_id":"hQJi65uTRz","event_type":"form_response",
                     "form_response":{"form_id":"YDJ9dj","token":"4969bac7b56e83a82ad060f0ae57faed",
                        "submitted_at":"2017-10-04T20:42:05Z","definition":{"id":"YDJ9dj",
                        "title":"nuevo","fields":[{"id":"62757082","title":"hola","type":"short_text",
                        "allow_multiple_selections":False,"allow_other_choice":False},{"id":"62757145",
                        "title":"si","type":"multiple_choice","allow_multiple_selections":False,"allow_other_choice":False}]},
                        "answers":[{"type":"text","text":"Lorem ipsum dolor","field":{"id":"62757082","type":"short_text"}},
                        {"type":"choice","choice":{"label":"Barcelona"},"field":{"id":"62757145","type":"multiple_choice"}}]}}


    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        self.assertIsInstance(self.controller._connection_object, TypeFormConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        self.assertTrue(self.controller._client)

    def test_test_connection(self):
        """
        Método que testea el test_connection, se asume que los paŕametros de entrada son validos por lo tanto debe retornar True
        """
        result = self.controller.test_connection()
        self.assertTrue(result)

    def test_create_webhook(self):
        """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
        webhook de la aplicación"""
        result = self.controller.create_webhook()
        count_end = Webhook.objects.filter(plug=self.plug).count()
        webhook = Webhook.objects.last()
        result_view = self.controller.view_webhook
        self.assertEqual(count_end,1)
        self.assertTrue(result)
        self.assertEqual(result_view['id'], webhook.generated_id)
        self.controller.delete_webhook(webhook_id=webhook.id)

    def test_delete_webhook(self):
        result_create = self.controller.create_webhook()
        webhook = Webhook.objects.last()
        self.controller.delete_webhook(webhook_id=webhook.id)
        try:
            result_view = self.controller.view_webhook(webhook_id=webhook.id)
            result = False
        except:
            result = True
        self.assertTrue(result)

    def test_get_action_specification_options(self):
        """Testea que retorne los action specification de manera correcta, en este caso los formularios"""
        action_specification_id = self.specification.id
        result = self.controller.get_action_specification_options(action_specification_id)
        _form = None
        for i in result:
            if i["id"] == os.environ.get("TEST_TYPEFORM_FORM"):
                _form = i["id"]
        self.assertIsInstance(result, tuple)
        self.assertEqual(_form, os.environ.get("TEST_TYPEFORM_FORM"))

    def test_has_webhook(self):
        """Testea que el método retorne True"""
        result = self.controller.has_webhook()
        self.assertTrue(result)

    def test_download_source_data(self):
        """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
        self.controller.download_source_data(self.plug.connection.related_connection, self.plug, answer=self.hook)
        count_store = StoredData.objects.filter(connection=self.connection, plug=self.plug).count()
        count_history = DownloadHistory.objects.all().count()
        self.assertNotEqual(count_store, 0)
        self.assertNotEqual(count_history, 0)


    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.controller.download_to_stored_data(self.plug.connection.related_connection, self.plug,
                                                         answer=self.hook)

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

    def test_do_webhook_process(self):
        """Simula un dato de entrada (self.hook), se crea un webhook y se verifica que retorne
        un status code =200, al final se borra el webhook"""
        self.controller.create_webhook()
        webhook = Webhook.objects.last()
        result = self.controller.do_webhook_process(body=self.hook, webhook_id=webhook.id)
        self.assertEqual(result.status_code, 200)
