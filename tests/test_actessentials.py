import os
import re
from apps.gp.map import MapField
from django.test import TestCase
from collections import OrderedDict
from apps.gp.enum import ConnectorEnum
from django.contrib.auth.models import User
from apps.gp.controllers.crm import ActEssentialsController
from apps.gp.models import Connection, ActEssentialsConnection, Action, Plug, ActionSpecification, \
    PlugActionSpecification, Webhook, StoredData, Gear, GearMap, GearMapData
from apps.history.models import DownloadHistory



class ActEssentialsControllerTestCases(TestCase):
    """
    """
    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="nrincon@grplug.com", password="Prueba#2017")

        connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.ActEssentials.value
        }
        cls.connection_source = Connection.objects.create(**connection)

        _connection_source = {
            "connection": cls.connection_source,
            "name": "ConnectionTest Source",
            "api_key": os.environ.get('ACTESSENTIALS_API_KEY'),
            "connection_id": ConnectorEnum.ActEssentials.value,
        }

        cls.actessentials_connection_source = ActEssentialsConnection.objects.create(**_connection_source)

        cls.connection_target = Connection.objects.create(**connection)

        _connection_target = {
            "connection": cls.connection_target,
            "name": "ConnectionTest Source",
            "api_key": os.environ.get('ACTESSENTIALS_API_KEY'),
            "connection_id": ConnectorEnum.ActEssentials.value+1,
        }
        cls.actessentials_connection_target = ActEssentialsConnection.objects.create(**_connection_target)

        action_source_1 = Action.objects.get(connector_id=ConnectorEnum.ActEssentials.value, action_type="source",
                                           name="new contact", is_active=True)
        action_source_2 = Action.objects.get(connector_id=ConnectorEnum.ActEssentials.value, action_type="source",
                                            name="new opportunity", is_active=True)

        actessentials_plug_source_1 = {
            "name": "PlugTest Source 1",
            "connection": cls.connection_source,
            "action": action_source_1,
            "plug_type": "source",
            "user": cls.user,
            "is_active": True
        }

        actessentials_plug_source_2 = {
            "name": "PlugTest Source 2",
            "connection": cls.connection_source,
            "action": action_source_2,
            "plug_type": "source",
            "user": cls.user,
            "is_active": True
        }

        cls.plug_source_1 = Plug.objects.create(**actessentials_plug_source_1)
        cls.plug_source_2 = Plug.objects.create(**actessentials_plug_source_2)

        action_target_1 = Action.objects.get(connector_id=ConnectorEnum.ActEssentials.value, action_type="target",
                                           name="create contact", is_active=True)
        action_target_2 = Action.objects.get(connector_id=ConnectorEnum.ActEssentials.value, action_type="target",
                                             name="create opportunity", is_active=True)

        actessentials_plug_target_1 = {
            "name": "PlugTest Target 1",
            "connection": cls.connection_target,
            "action": action_target_1,
            "plug_type": "target",
            "user": cls.user,
            "is_active": True
        }

        actessentials_plug_target_2 = {
            "name": "PlugTest Target 2",
            "connection": cls.connection_target,
            "action": action_target_2,
            "plug_type": "target",
            "user": cls.user,
            "is_active": True
        }

        cls.plug_target_1 = Plug.objects.create(**actessentials_plug_target_1)
        cls.plug_target_2 = Plug.objects.create(**actessentials_plug_target_2)

        # Gear 1: contact ; Gear 2: opportunity
        gear_1 = {
            "name": "Gear 1",
            "user": cls.user,
            "source": cls.plug_source_1,
            "target": cls.plug_target_1,
            "is_active": True
        }
        gear_2 = {
            "name": "Gear 2",
            "user": cls.user,
            "source": cls.plug_source_2,
            "target": cls.plug_target_2,
            "is_active": True
        }
        cls.gear_1 = Gear.objects.create(**gear_1)
        cls.gear_2 = Gear.objects.create(**gear_2)
        cls.gear_map_1 = GearMap.objects.create(gear=cls.gear_1)
        cls.gear_map_2 = GearMap.objects.create(gear=cls.gear_2)

        # Contact
        map_data_1 = {"target_name": "firstName", "source_value": "%%firstName%%", "gear_map": cls.gear_map_1}
        map_data_2 = {"target_name": "lastName", "source_value": "%%lastName%%", "gear_map": cls.gear_map_1}
        map_data_3 = {"target_name": "company", "source_value": "%%company%%", "gear_map": cls.gear_map_1}
        map_data_4 = {"target_name": "jobTitle", "source_value": "%%jobTitle%%", "gear_map": cls.gear_map_1}
        map_data_5 = {"target_name": "emailAddress", "source_value": "%%emailAddress%%", "gear_map": cls.gear_map_1}
        map_data_6 = {"target_name": "altEmailAddress", "source_value": "%%altEmailAddress%%", "gear_map": cls.gear_map_1}
        map_data_7 = {"target_name": "businessPhone", "source_value": "%%businessPhone%%", "gear_map": cls.gear_map_1}
        map_data_8 = {"target_name": "mobilePhone", "source_value": "%%mobilePhone%%", "gear_map": cls.gear_map_1}
        map_data_9 = {"target_name": "homePhone", "source_value": "%%homePhone%%", "gear_map": cls.gear_map_1}
        map_data_10 = {"target_name": "website", "source_value": "%%website%%", "gear_map": cls.gear_map_1}
        map_data_11 = {"target_name": "linkedinUrl", "source_value": "%%linkedinUrl%%", "gear_map": cls.gear_map_1}
        map_data_12 = {"target_name": "birthday", "source_value": "%%birthday%%", "gear_map": cls.gear_map_1}

        # Opportunity
        map_data_13 = {"target_name": "title", "source_value": "%%title%%", "gear_map": cls.gear_map_2}
        map_data_14 = {"target_name": "stage", "source_value": "%%stage%%", "gear_map": cls.gear_map_2}
        map_data_15 = {"target_name": "description", "source_value": "%%description%%", "gear_map": cls.gear_map_2}
        map_data_16 = {"target_name": "total", "source_value": "%%total%%", "gear_map": cls.gear_map_2}
        map_data_17 = {"target_name": "currency", "source_value": "%%currency%%", "gear_map": cls.gear_map_2}
        map_data_18 = {"target_name": "notes", "source_value": "%%notes%%", "gear_map": cls.gear_map_2}
        map_data_19 = {"target_name": "estimatedClose", "source_value": "%%estimatedClose%%", "gear_map": cls.gear_map_2}
        map_data_20 = {"target_name": "actualClose", "source_value": "%%actualClose%%", "gear_map": cls.gear_map_2}
        map_data_21 = {"target_name": "notes", "source_value": "%%notes%%", "gear_map": cls.gear_map_2}

        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)
        GearMapData.objects.create(**map_data_4)
        GearMapData.objects.create(**map_data_5)
        GearMapData.objects.create(**map_data_6)
        GearMapData.objects.create(**map_data_7)
        GearMapData.objects.create(**map_data_8)
        GearMapData.objects.create(**map_data_9)
        GearMapData.objects.create(**map_data_10)
        GearMapData.objects.create(**map_data_11)
        GearMapData.objects.create(**map_data_12)
        GearMapData.objects.create(**map_data_13)
        GearMapData.objects.create(**map_data_14)
        GearMapData.objects.create(**map_data_15)
        GearMapData.objects.create(**map_data_16)
        GearMapData.objects.create(**map_data_17)
        GearMapData.objects.create(**map_data_18)
        GearMapData.objects.create(**map_data_19)
        GearMapData.objects.create(**map_data_20)
        GearMapData.objects.create(**map_data_21)

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self.controller_source_1 = ActEssentialsController(self.plug_source_1.connection.related_connection,
                                                          self.plug_source_1)
        self.controller_source_2 = ActEssentialsController(self.plug_source_2.connection.related_connection,
                                                          self.plug_source_2)
        self.controller_target_1 = ActEssentialsController(self.plug_target_1.connection.related_connection,
                                                          self.plug_target_1)
        self.controller_target_2 = ActEssentialsController(self.plug_target_2.connection.related_connection,
                                                          self.plug_target_2)

    def _get_fields_contact(self):
        return [
            {'name': 'firstName', 'label': 'firstName', 'type': 'varchar', 'required': True},
            {'name': 'lastName', 'label': 'lastName', 'type': 'varchar', 'required': False},
            {'name': 'company', 'label': 'company', 'type': 'varchar', 'required': False},
            {'name': 'jobTitle', 'label': 'jobTitle', 'type': 'varchar', 'required': False},
            {'name': 'emailAddress', 'label': 'emailAddress', 'type': 'email', 'required': False},
            {'name': 'altEmailAddress', 'label': 'altEmailAddress', 'type': 'email', 'required': False},
            {'name': 'businessPhone', 'label': 'businessPhone', 'type': 'varchar', 'required': False},
            {'name': 'mobilePhone', 'label': 'mobilePhone', 'type': 'varchar', 'required': False},
            {'name': 'homePhone', 'label': 'homePhone', 'type': 'varchar', 'required': False},
            {'name': 'website', 'label': 'website', 'type': 'varchar', 'required': False},
            {'name': 'linkedinUrl', 'label': 'linkedinUrl', 'type': 'varchar', 'required': False},
            {'name': 'birthday', 'label': 'birthday', 'type': 'varchar', 'required': False},
        ]

    def _get_fields_opportunity(self):
        return [
            {'name': 'title', 'label': 'title', 'type': 'varchar', 'required': True},
            {'name': 'stage', 'label': 'stage', 'type': 'varchar', 'required': True},
            {'name': 'description', 'label': 'description', 'type': 'varchar', 'required': False},
            {'name': 'total', 'label': 'total', 'type': 'varchar', 'required': False},
            {'name': 'currency', 'label': 'currency', 'type': 'varchar', 'required': False},
            {'name': 'notes', 'label': 'notes', 'type': 'varchar', 'required': False},
            {'name': 'estimatedClose', 'label': 'estimatedClose', 'type': 'varchar', 'required': False},
            {'name': 'actualClose', 'label': 'actualClose', 'type': 'varchar', 'required': False},
            {'name': 'notes', 'label': 'notes', 'type': 'varchar', 'required': False},
        ]

    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        self.assertIsInstance(self.controller_source_1._connection_object, ActEssentialsConnection)
        self.assertIsInstance(self.controller_source_2._connection_object, ActEssentialsConnection)
        self.assertIsInstance(self.controller_target_1._connection_object, ActEssentialsConnection)
        self.assertIsInstance(self.controller_target_2._connection_object, ActEssentialsConnection)
        self.assertIsInstance(self.controller_source_1._plug, Plug)
        self.assertIsInstance(self.controller_source_2._plug, Plug)
        self.assertIsInstance(self.controller_target_1._plug, Plug)
        self.assertIsInstance(self.controller_target_2._plug, Plug)
        self.assertTrue(self.controller_source_1.client)
        self.assertTrue(self.controller_source_2.client)
        self.assertTrue(self.controller_target_1.client)
        self.assertTrue(self.controller_target_2.client)

    def test_test_connection(self):
        """
        Comprueba metodo test_connection()
        """
        result1 = self.controller_source_1.test_connection()
        result2 = self.controller_source_2.test_connection()
        result3 = self.controller_target_1.test_connection()
        result4 = self.controller_target_2.test_connection()
        self.assertIsNot(result1, None)
        self.assertIsNot(result2, None)
        self.assertIsNot(result3, None)
        self.assertIsNot(result4, None)

    def test_has_webhook(self):
        """
        Resultado esperado: FALSE
        """
        self.assertFalse(self.controller_source_1.has_webhook)
        self.assertFalse(self.controller_source_2.has_webhook)
        self.assertFalse(self.controller_target_1.has_webhook)
        self.assertFalse(self.controller_target_2.has_webhook)

    def test_download_to_stored_data(self):
        """
        Test realizado con action source 1: new contact
        """
        result_1 = self.controller_source_1.download_to_stored_data(self.plug_source_1.connection.related_connection,
                                                                self.plug_source_1)

        result_2 = self.controller_source_2.download_to_stored_data(self.plug_source_2.connection.related_connection,
                                                                    self.plug_source_2)
        self.assertIn('downloaded_data', result_1)
        self.assertIsInstance(result_1['downloaded_data'], list)
        self.assertIsInstance(result_1['downloaded_data'][-1], dict)
        self.assertIn('identifier', result_1['downloaded_data'][-1])
        self.assertIsInstance(result_1['downloaded_data'][-1]['identifier'], dict)
        self.assertIn('name', result_1['downloaded_data'][-1]['identifier'])
        self.assertIn('value', result_1['downloaded_data'][-1]['identifier'])
        self.assertIsInstance(result_1['downloaded_data'][-1], dict)
        self.assertIn('raw', result_1['downloaded_data'][-1])
        self.assertIsInstance(result_1['downloaded_data'][-1]['raw'], dict)
        self.assertIn('is_stored', result_1['downloaded_data'][-1])
        self.assertIsInstance(result_1['downloaded_data'][-1]['is_stored'], bool)
        self.assertIn('last_source_record', result_1)
        self.assertIsNotNone(result_1['last_source_record'])
        
        self.assertIn('downloaded_data', result_2)
        self.assertIsInstance(result_2['downloaded_data'], list)
        self.assertIsInstance(result_2['downloaded_data'][-1], dict)
        self.assertIn('identifier', result_2['downloaded_data'][-1])
        self.assertIsInstance(result_2['downloaded_data'][-1]['identifier'], dict)
        self.assertIn('name', result_2['downloaded_data'][-1]['identifier'])
        self.assertIn('value', result_2['downloaded_data'][-1]['identifier'])
        self.assertIsInstance(result_2['downloaded_data'][-1], dict)
        self.assertIn('raw', result_2['downloaded_data'][-1])
        self.assertIsInstance(result_2['downloaded_data'][-1]['raw'], dict)
        self.assertIn('is_stored', result_2['downloaded_data'][-1])
        self.assertIsInstance(result_2['downloaded_data'][-1]['is_stored'], bool)
        self.assertIn('last_source_record', result_2)
        self.assertIsNotNone(result_2['last_source_record'])

    def test_send_stored_data(self):
        """
        Test realizado con action target 1: create contact
        """
        data = {'email': 'nrincon@grplug.com'}
        data_list = [OrderedDict(data)]
        result_1 = self.controller_target_1.send_stored_data(data_list)
        result_2 = self.controller_target_2.send_stored_data(data_list)
        

        self.assertIsInstance(result_1, list)
        self.assertIsInstance(result_1[-1], dict)
        self.assertIn('data', result_1[-1])
        self.assertIn('response', result_1[-1])
        self.assertIn('sent', result_1[-1])
        self.assertIn('identifier', result_1[-1])
        self.assertIsInstance(result_1[-1]['data'], dict)
        self.assertIsInstance(result_1[-1]['response'], dict)
        self.assertIsInstance(result_1[-1]['sent'], bool)
        self.assertEqual(result_1[-1]['data'], dict(data_list[0]))

        self.assertIsInstance(result_2, list)
        self.assertIsInstance(result_2[-1], dict)
        self.assertIn('data', result_2[-1])
        self.assertIn('response', result_2[-1])
        self.assertIn('sent', result_2[-1])
        self.assertIn('identifier', result_2[-1])
        self.assertIsInstance(result_2[-1]['data'], dict)
        self.assertIsInstance(result_2[-1]['response'], dict)
        self.assertIsInstance(result_2[-1]['sent'], bool)
        self.assertEqual(result_2[-1]['data'], dict(data_list[0]))

    def test_get_target_fields(self):
        """
        Se espera que la variable result sea igual al resultado del metodo local _get_fields
        """
        result_1 = self.controller_target_1.get_target_fields()
        result_2 = self.controller_target_2.get_target_fields()
        self.assertEqual(result_1, self._get_fields_contact())
        self.assertEqual(result_2, self._get_fields_opportunity())

    def test_get_mapping_fields(self):
        """
        Se verifica la estructura y el tipo de datos de get_mapping_fields,
        utilizando la accion target 2: create opportunity
        """
        result_1 = self.controller_target_1.get_mapping_fields()
        result_2 = self.controller_target_2.get_mapping_fields()

        self.assertIsInstance(result_1, list)
        self.assertIsInstance(result_1[0], MapField)

        self.assertIsInstance(result_2, list)
        self.assertIsInstance(result_2[0], MapField)
