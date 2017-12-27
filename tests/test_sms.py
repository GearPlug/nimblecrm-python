from django.test import TestCase
from django.contrib.auth.models import User
from apps.gp.models import Connection, SMSConnection, Plug, Action, Gear
from apps.gp.controllers.im import SMSController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class SMSControllerTestCases(TestCase):
    """
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='lrubiano@grplug.com', email='lrubiano@grplug.com',
                                       password='Prueba#2017')
        # SOURCE CONNECTION
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.SMS.value
        }
        cls.connection = Connection.objects.create(**connection)

        sms_connection = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'connection_user':'',
            'connection_password':''
        }
        cls.sms_connection = SMSConnection.objects.create(**sms_connection)

        action = Action.objects.get(connector_id=ConnectorEnum.SMS.value, action_type='target',
                                           name='send sms', is_active=True)

        sms_plug = {
            'name': 'PlugTest',
            'connection': cls.connection,
            'action': action,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }
        cls.plug = Plug.objects.create(**sms_plug)

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.
        """
        self.controller = SMSController(self.plug.connection.related_connection, self.plug)

        self.target_structure = [{'name': 'number_to', 'label': 'to', 'type': 'varchar', 'required': True},
                {'name': 'message', 'label': 'text', 'type': 'varchar', 'required': True}, ]

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.
        """
        self.assertIsInstance(self.controller._connection_object, SMSConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        self.assertNotEqual(self.controller.client, None)
        self.assertNotEqual(self.controller.sender_identifier, None)
        self.assertTrue(self.controller.is_active)

    def test_test_connection(self):
        """
        Verifica que la conexión este establecida
        """
        result = self.controller.test_connection()
        self.assertTrue(result)

    def test_get_mapping_fields(self):
        """Comprueba que el resultado sea una instancia de Mapfields
        """
        result = self.controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertTrue(result)
        self.assertIsInstance(result[0], MapField)

    def test_get_target_fields(self):
        """
        Comprueba que traiga los fields esperados
        """
        result = self.controller.get_target_fields()
        self.assertEqual(result, self.target_structure)

    def test_send_stored_data(self):
        """simula un dato de entrada y comprueba que retrorne una lista de acuerdo a los parámetros establecidos"""
        data_list=[OrderedDict({"message": "test message", 'number_to':"+573132192527"})]
        result = self.controller.send_stored_data(data_list)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)
        self.assertIn('data', result[-1])
        self.assertIn('response', result[-1])
        self.assertIn('sent', result[-1])
        self.assertTrue(result[0]['sent'])
        self.assertIn('identifier', result[-1])
        self.assertIsInstance(result[-1]['data'], dict)
        self.assertIsInstance(result[-1]['response'], str)
        self.assertIsInstance(result[-1]['sent'], bool)
        self.assertEqual(result[-1]['data'], dict(data_list[0]))
