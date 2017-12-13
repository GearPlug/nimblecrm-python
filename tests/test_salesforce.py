import ast
import json
import os
from django.conf import settings
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.shortcuts import HttpResponse
from apps.gp.models import Connection, SalesforceConnection, Plug, Action, ActionSpecification, PlugActionSpecification, \
    Gear, GearMap, StoredData, GearMapData, Webhook
from apps.history.models import DownloadHistory, SendHistory
from apps.gp.controllers.crm import SalesforceController
from salesforce.client import Client as SalesforceClient
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict


class SalesforceControllerTestCases(TestCase):
    """Casos de prueba del controlador Salesforce.

        Variables de entorno:
            TEST_SALESFORCE_TOKEN: String: User Token.

    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
        cls.user = User.objects.create(username='ingmferrer', email='ingferrermiguel@gmail.com',
                                       password='nopass100realnofake')
        connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Salesforce.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        salesforce_connection1 = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'token': json.dumps(ast.literal_eval(os.environ.get('TEST_SALESFORCE_TOKEN'))),
        }
        cls.salesforce_connection1 = SalesforceConnection.objects.create(**salesforce_connection1)

        cls.connection_target = Connection.objects.create(**connection)

        salesforce_connection2 = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'token': json.dumps(ast.literal_eval(os.environ.get('TEST_SALESFORCE_TOKEN'))),
        }
        cls.salesforce_connection2 = SalesforceConnection.objects.create(**salesforce_connection2)

        action_source = Action.objects.get(connector_id=ConnectorEnum.Salesforce.value, action_type='source',
                                           name='new event', is_active=True)

        salesforce_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_source = Plug.objects.create(**salesforce_plug_source)

        action_target = Action.objects.get(connector_id=ConnectorEnum.Salesforce.value, action_type='target',
                                           name='create lead', is_active=True)

        salesforce_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True
        }
        cls.plug_target = Plug.objects.create(**salesforce_plug_target)

        cls.source_specification_1 = ActionSpecification.objects.get(action=action_source, name='sobject')

        cls.target_specification_2 = ActionSpecification.objects.get(action=action_source, name='event')

        _dict_source_specification = {
            'plug': cls.plug_source,
            'action_specification': cls.source_specification_1,
            'value': 'user'
        }
        PlugActionSpecification.objects.create(**_dict_source_specification)

        _dict_target_specification = {
            'plug': cls.plug_source,
            'action_specification': cls.target_specification_2,
            'value': 'after insert'
        }
        PlugActionSpecification.objects.create(**_dict_target_specification)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_1 = {'target_name': 'LastName', 'source_value': '%%FirstName%%', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'IsConverted', 'source_value': 'False', 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'Status', 'source_value': 'Open - Not Contacted', 'gear_map': cls.gear_map}
        map_data_4 = {'target_name': 'IsUnreadByOwner', 'source_value': 'False', 'gear_map': cls.gear_map}
        map_data_5 = {'target_name': 'Company', 'source_value': 'NA', 'gear_map': cls.gear_map}
        map_data_6 = {'target_name': 'FirstName', 'source_value': '%%FirstName%%', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)
        GearMapData.objects.create(**map_data_4)
        GearMapData.objects.create(**map_data_5)
        GearMapData.objects.create(**map_data_6)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        # self.client = Client()
        self.source_controller = SalesforceController(self.plug_source.connection.related_connection, self.plug_source)
        self.target_controller = SalesforceController(self.plug_target.connection.related_connection, self.plug_target)

        self.hook = {'userId': '0056A000000iJKzQAM', 'old': [], 'new': [
            {'NeedsNewPassword': True, 'EndDay': '23', 'ReceivesAdminInfoEmails': True, 'IsExtIndicatorVisible': False,
             'LastModifiedById': '0056A000000iJKzQAM', 'Email': 'mdfingcisco3@gmail.com',
             'JigsawImportLimitOverride': 300, 'DataStorageUsage': 0, 'DefaultGroupNotificationFrequency': 'N',
             'CreatedDate': '2017-12-11T15:44:41.000+0000', 'FirstName': 'Dario', 'IsSystemControlled': False,
             'SharingType': 'CsnExternal', 'StartDay': '6', 'Alias': 'mferr', 'FileStorageUsage': 0,
             'SystemModstamp': '2017-12-11T15:44:41.000+0000', 'LocaleSidKey': 'es_VE', 'UserType': 'CsnOnly',
             'IsActive': True, 'CreatedById': '0056A000000iJKzQAM', 'LastName': 'Espinoza', 'ReceivesInfoEmails': True,
             'Id': '123456789', 'DigestFrequency': 'D', 'LastModifiedDate': '2017-12-11T15:44:41.000+0000',
             'TimeZoneSidKey': 'America/Caracas', 'IsBadged': False, 'ProfileId': '00e6A000001G4KJQA0',
             'IsProfilePhotoActive': False, 'HasRollups': False, 'LanguageLocaleKey': 'es',
             'CommunityNickname': 'mdfingcisco3', 'ForecastEnabled': False, 'StorageUsage': 0,
             'IsCheckoutEnabled': False, 'Username': 'mdfingcisco3@gmail.com',
             'attributes': {'type': 'User', 'url': '/services/data/v41.0/sobjects/User/0056A000000wdNoQAI'},
             'EmailEncodingKey': 'ISO-8859-1'}]}

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.source_controller._connection_object, SalesforceConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        # Error 1
        # self.assertIsInstance(self.controller._connector, ConnectorEnum.OdooCRM)
        self.assertIsInstance(self.source_controller._client, SalesforceClient)

    def test_do_webhook_process(self):
        """Comprueba que la llamada al metodo devuelva un HTTP Response con un Status Code específico y que
        como resultado del proceso haya data guardada en StoredData.

        """
        _dict = {
            'name': 'salesforce',
            'plug': self.plug_source,
            'url': settings.WEBHOOK_HOST,
            'expiration': '',
            'generated_id': '1',
            'is_active': True
        }
        webhook = Webhook.objects.create(**_dict)
        result = self.source_controller.do_webhook_process(self.hook, POST=True, webhook_id=webhook.id)
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)

    def test_get_mapping_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.source_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_download_to_stored_data(self):
        """Comprueba que la llamada al metodo devuelva un diccionario y la existencia de los atributos necesarios y
        su respectivo tipo de dato almacenado como valor.

        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, event=self.hook)

        self.assertIsInstance(result, dict)
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

    def test_download_source_data(self):
        """Comprueba que la llamada al metodo haya guardado data en StoredData y que se hayan creado registros de
        historial.

        """
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source, event=self.hook)

        qs = StoredData.objects.order_by('object_id').values_list('object_id', flat=True).distinct()
        for lead in qs:
            count = DownloadHistory.objects.filter(identifier={'name': 'id', 'value': lead}).count()
            self.assertGreater(count, 0)

    def test_send_stored_data(self):
        """Guarda datos en StoredData y luego los envía la data mapeada al servidor CRM, luego comprueba de que
        el valor devuelto sea una lista además de comprobar que esté guardando registros en SendHistory.

        """
        result1 = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                              self.plug_source, event=self.hook)
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
