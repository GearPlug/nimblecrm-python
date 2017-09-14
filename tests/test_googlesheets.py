from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController
from apps.gp.models import Connection, ConnectorEnum, GoogleSpreadSheetsConnection, Action, Plug, ActionSpecification, PlugActionSpecification, \
    GoogleSpreadSheetsConnection
from django.contrib.auth.models import User
from django.test import TestCase, Client
import os


class GoogleSpreadSheetsControllerTestCases(TestCase):
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='lyrubiano', email='lyrubiano5@gmail.com',
                                       password='Prueba#2017')
        _dict = {
            'user': cls.user,
            'connector_id': ConnectorEnum.GoogleSpreadSheets.value
        }

        cls.connection = Connection.objects.create(**_dict)

        token = os.environ.get('token')

        _dict2 = {
            'connection': cls.connection,
            'name': 'ConnectionTest',
            'token': token,
        }
        cls.mysql_connection = GoogleSpreadSheetsConnection.objects.create(**_dict2)

        action = Action.objects.get(connector_id=ConnectorEnum.MailChimp.value, action_type='target', name='subscribe',
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

        cls.specification = ActionSpecification.objects.get(action=action, name='list')


        _dict4 = {
            'plug': cls.plug,
            'action_specification': cls.specification,
            'value': 'id'
        }
        PlugActionSpecification.objects.create(**_dict4)

    def setUp(self):
        self.controller = GoogleSpreadSheetsController(self.plug.connection.related_connection, self.plug)
        self._token = os.environ.get('token')
        self._client = Client(access_token=self._token)

    def test_controller(self):
        self.assertIsInstance(self.controller._connection_object,
                              GoogleSpreadSheetsConnection)
        self.assertIsInstance(self.controller._plug, Plug)
        self.assertIsInstance(self.controller._client, )

    # def test_create_connection(self):
    #     count = list(GoogleSpreadSheetsConnection.objects.all())
    #     result = self.controller.create_connection()
    #     count2= list(GoogleSpreadSheetsConnection.objects.all())
    #     self.assertEqual(count+1, count2)

    # def test_test_connection(self):
    #     result = self.controller.test_connection()
    #     self.assertTrue(result)

    # def test_upate_connection_object_credentials(self):
    #     self._connection_object.credentials_json = self._credential.to_json()
    #     self._connection_object.save()







    # def test_get_target_fields(self):
    #     result=self.controller.get_target_fields()
    #     self.assertEqual(result, self._get_fields())
    #
    # def test_get_mapping_fields(self):
    #     result=self.controller.get_mapping_fields()
    #     self.assertIsInstance(result, list)
    #     self.assertIsInstance(result[0], MapField)
    #
    # def test_get_action_specification_options(self):
    #     action_specification_id=self.specification.id
    #     result = self.controller.get_action_specification_options(action_specification_id)
    #     listss = tuple({'id': c['id'], 'name': c['name']} for c in self._client.get_lists()['lists'])
    #     self.assertIsInstance(result, tuple)
    #     self.assertEqual(result, listss)
