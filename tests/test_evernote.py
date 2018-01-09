import os
from collections import OrderedDict

from django.contrib.auth.models import User
from django.test import TestCase
from evernote.api.client import EvernoteClient

from apps.gp.controllers.ofimatic import EvernoteController
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Connection, EvernoteConnection, Action, Plug, Gear, GearMap, GearMapData, StoredData
from apps.history.models import DownloadHistory
from apps.gp.map import MapField
import time


class EvernoteControllerTestCases(TestCase):
    """
        TEST_EVERNOTE_TOKEN : string con el token.
        TEST_EVERNOTE_USER_ID
        TEST_EVERNOTE_GUID_2
        TEST_EVERNOTE_GUID
    """
    fixtures = ["gp_base.json"]

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username="test", email="lyrubiano5@gmail.com", password="Prueba#2017")

        _dict_connection = {
            "user": cls.user,
            "connector_id": ConnectorEnum.Evernote.value
        }
        cls.connection = Connection.objects.create(**_dict_connection)

        _dict_evernote_connection = {
            'connection':cls.connection,
            'name':'ConnectionTest',
            'token':os.environ.get('TEST_EVERNOTE_TOKEN'),
            # 'user_id':os.environ.get('TEST_EVERNOTE_USER_ID')
        }

        cls.evernote_connection = EvernoteConnection.objects.create(**_dict_evernote_connection)

        # Buscar acciones de Evernote
        action_source = Action.objects.get(connector_id=ConnectorEnum.Evernote.value, action_type="source",
                                           name="new note created", is_active=True)

        action_target = Action.objects.get(connector_id=ConnectorEnum.Evernote.value, action_type="target",
                                           name="create note", is_active=True)

        _dict_evernote_plug_source = {
            "name": "PlugTest Source",
            "connection": cls.connection,
            "action": action_source,
            "plug_type": "source",
            "user": cls.user,
            "is_active": True
        }
        cls.plug_source = Plug.objects.create(**_dict_evernote_plug_source)

        _dict_evernote_plug_target = {
            "name": "PlugTest Source",
            "connection": cls.connection,
            "action": action_target,
            "plug_type": "target",
            "user": cls.user,
            "is_active": True
        }
        cls.plug_target = Plug.objects.create(**_dict_evernote_plug_target)

        gear = {
            "name": "Gear 1",
            "user": cls.user,
            "source": cls.plug_source,
            "target": cls.plug_target,
            "is_active": True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_1 = {'target_name': 'name', 'source_value': '%%title%%', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'oldid', 'source_value': '%%content%%', 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'id', 'source_value': '', 'gear_map': cls.gear_map}

        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)

    def setUp(self):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.
        """
        self.controller_source= EvernoteController(self.plug_source.connection.related_connection,self.plug_source)
        self.controller_target= EvernoteController(self.plug_target.connection.related_connection,self.plug_target)

    def _data(self):
        return {'id': 'd0ce2463-8507-4b71-bb65-68e23ad665e9',
                'data': {'title': 'nota de prueba 005', 'created': '1513109513000',
                         'id': 'd0ce2463-8507-4b71-bb65-68e23ad665e9', 'content': 'nota de prueba 005'}}

    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        self.assertIsInstance(self.controller_source._connection_object, EvernoteConnection)
        self.assertIsInstance(self.controller_target._connection_object, EvernoteConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertIsInstance(self.controller_target._plug, Plug)
        self.assertIsInstance(self.controller_source._client, EvernoteClient)
        self.assertIsInstance(self.controller_target._client, EvernoteClient)

    def test_test_connection(self):
        """
        MÃ©todo que testea el test_connection, se asume que los paÅ•ametros de entrada son validos por lo tanto debe retornar True
        """
        time.sleep(10)
        result1 = self.controller_source.test_connection()
        result2 = self.controller_target.test_connection()
        self.assertTrue(result1)
        self.assertTrue(result2)

    def test_download_source_data_using_webhook(self):
        """
        Simula un dato de entrada (self.in_data) y se verifica que este dato
        se cree en las tablas DownloadHistory y StoreData.
        Si bien es cierto que este controlador no usa webhooks, se realiza esta prueba
        debido a que la modalidad de webhooks no esta del todo descartada, esta posiblidad esta abierta
        ya que existe una opcion en Evernote para activar una especie de webhook donde la
        plataforma envia notificaciones predeterminadas por equipo de desarrollo de la aplicacion
        para luego realizar solicitudes especificas correspondientes a dichas notificaciones.
        """
        time.sleep(10)
        noteStore = self.controller_source._client.get_note_store()
        nota = noteStore.getNote(os.environ.get('TEST_EVERNOTE_TOKEN'),
                                 os.environ.get('TEST_EVERNOTE_GUID'),
                                 True, False, False, False)
        self.controller_source.download_source_data(self.plug_source.connection.related_connection,
                                                    self.plug_source, data = nota)
        count_store = StoredData.objects.filter(connection=self.connection, plug=self.plug_source).count()
        count_history = DownloadHistory.objects.all().count()
        self.assertNotEqual(count_store, 0)
        self.assertNotEqual(count_history, 0)

    def test_download_source_data(self):
        """
        Simula un dato de entrada (self.in_data) y se verifica que este dato
        se cree en las tablas DownloadHistory y StoreData
        """
        time.sleep(10)
        self.controller_source.download_source_data(self.plug_source.connection.related_connection,
                                                    self.plug_source, data=None)
        count_store = StoredData.objects.filter(connection=self.connection, plug=self.plug_source).count()
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
        time.sleep(10)
        noteStore = self.controller_source._client.get_note_store()
        nota = noteStore.getNote(os.environ.get('TEST_EVERNOTE_TOKEN'),
                                 os.environ.get('TEST_EVERNOTE_GUID'),
                                 True, False, False, False)
        result = self.controller_source.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, data=nota)
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
        """
        """
        time.sleep(10)
        result = self.controller_target.get_target_fields()
        spected = [
            {'name': 'title', 'type': 'varchar', 'required': True},
            {'name': 'content', 'type': 'varchar', 'required': True}
        ]
        self.assertIsInstance(result[-1], dict)
        self.assertEqual(result, spected)

    def test_get_mapping_fields(self):
        """
        """
        time.sleep(10)
        result = self.controller_source.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_send_stored_data(self):
        """
        Simula un dato de entrada (self._data), y verifica que retorne una
        lista de acuerdo a los parÃ¡metros establecidos
        """
        time.sleep(10)
        data_list = [OrderedDict(self._data())]
        result = self.controller_target.send_stored_data(data_list)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)
        self.assertIn('data', result[-1])
        self.assertIn('response', result[-1])
        self.assertIn('sent', result[-1])
        self.assertIn('identifier', result[-1])
        self.assertIsInstance(result[-1]['data'], dict)
        self.assertIsInstance(result[-1]['response'], dict)
        self.assertIsInstance(result[-1]['sent'], bool)
        self.assertTrue(result[0]['sent'])

    def test_get_notes(self):
        """
        """
        time.sleep(10)
        result = self.controller_source.get_notes(os.environ.get('TEST_EVERNOTE_TOKEN'))
        self.assertIsInstance(result, list)
        for i in result:
            self.assertIsInstance(i, dict)
            self.assertTrue('title' in i.keys())
            self.assertTrue('id' in i.keys())
            self.assertTrue('content' in i.keys())

    def test_create_note(self):
        """
        """
        time.sleep(10)
        flag = False
        data = OrderedDict([('data', {'created': '1513109513000', 'content': 'nota de prueba 005',
                               'id': 'd0ce2463-8507-4b71-bb65-68e23ad665e9', 'title': 'nota de prueba 005'}),
                     ('id', 'd0ce2463-8507-4b71-bb65-68e23ad665e9')])
        create_note = self.controller_target.create_note(data=data)
        _guid_a = create_note.guid
        notes = self.controller_source.get_notes(os.environ.get('TEST_EVERNOTE_TOKEN'))
        for note in notes:
            if note['title'] == create_note.title and note['id'] == str(_guid_a):
                _guid_b = note['id']
                flag = True
        # self.controller_target.delete_note(guid=guid_b)
        self.assertTrue(flag)


