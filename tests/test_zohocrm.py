import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, ZohoCRMConnection, Plug, Action, \
    ActionSpecification, PlugActionSpecification, Gear, GearMap, GearMapData, StoredData, Webhook
from apps.gp.controllers.crm import ZohoCRMController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict
from apps.history.models import DownloadHistory, SendHistory

class ZohoCRMControllerTestCases(TestCase):
    """
    TEST_ZOHOCRM_TOKEN: String:
    TEST_ZOHOCRM_LIST: String, ID de una lista existente en la aplicación
    TEST_ZOHOCRM_USER: String, ID de un usuario existente en la aplicación
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='lrubiano@grplug.com',
                                       email='lrubiano@grplug.com',
                                       password='Prueba#2017')
        _dict_source_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.ZohoCRM.value
        }
        cls.source_connection = Connection.objects.create(**_dict_source_connection)

        _dict_target_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.ZohoCRM.value
        }
        cls.target_connection = Connection.objects.create(**_dict_target_connection)

        _dict_zohocrm_source_connection = {
            'connection': cls.source_connection,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_ZOHOCRM_TOKEN'),
        }
        cls.zohocrm_source_connection = ZohoCRMConnection.objects.create(**_dict_zohocrm_source_connection)

        _dict_zohocrm_target_connection = {
            'connection': cls.target_connection,
            'name': 'ConnectionTest',
            'token': os.environ.get('TEST_ZOHOCRM_TOKEN'),
        }
        cls.zohocrm_target_connection = ZohoCRMConnection.objects.create(**_dict_zohocrm_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.ZohoCRM.value,
                                    action_type='source',
                                    name='new feed',
                                    is_active=True)

        target_action = Action.objects.get(connector_id=ConnectorEnum.ZohoCRM.value,
                                           action_type='target',
                                           name='create feed',
                                           is_active=True)

        _dict_source_action = {
            'name': 'PlugTest',
            'connection': cls.source_connection,
            'action': source_action,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**_dict_source_action)

        _dict_target_action = {
            'name': 'PlugTest',
            'connection': cls.target_connection,
            'action': target_action,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**_dict_target_action)

        cls.source_specification = ActionSpecification.objects.get(action=source_action,
                                                         name='feed')

        cls.target_specification = ActionSpecification.objects.get(action=target_action,
                                                               name='feed')

        _dict_source_specification = {
            'plug': cls.plug_source,
            'action_specification': cls.source_specification,
            'value': os.environ.get('TEST_SOURCE_FEED')
        }
        PlugActionSpecification.objects.create(**_dict_source_specification)

        _dict_target_specification = {
            'plug': cls.plug_target,
            'action_specification': cls.target_specification,
            'value': os.environ.get('TEST_TARGET_FEED')
        }
        PlugActionSpecification.objects.create(**_dict_target_specification)

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        map_data_1 = {'target_name': 'Qty Ordered', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'Description', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'Reorder Level', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_4 = {'target_name': 'Tag', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_5 = {'target_name': 'Qty in Stock', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_6 = {'target_name': 'FirstNameVendor Name', 'source_value': '%%a%%', 'gear_map': cls.gear_map}
        map_data_7 = {'target_name': 'Product Name', 'source_value': '%%b%%', 'gear_map': cls.gear_map}
        map_data_8 = {'target_name': 'Product Category', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_9 = {'target_name': 'Product Owner', 'source_value': '%%a%%', 'gear_map': cls.gear_map}
        map_data_10 = {'target_name': 'Sales Start Date', 'source_value': '%%c%%', 'gear_map': cls.gear_map}
        map_data_11 = {'target_name': 'Taxable', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_12 = {'target_name': 'Support Expiry Date', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_13 = {'target_name': 'Commission Rate', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_14 = {'target_name': 'Qty in Demand', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_15 = {'target_name': 'Manufacturer', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_16 = {'target_name': 'Tax', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_17 = {'target_name': 'Modified By', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_18 = {'target_name': 'Support Start Date', 'source_value': '%%b%%', 'gear_map': cls.gear_map}
        map_data_19 = {'target_name': 'Usage Unit', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_20 = {'target_name': 'Created By', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_21 = {'target_name': 'Sales End Date', 'source_value': '%%a%%', 'gear_map': cls.gear_map}
        map_data_22 = {'target_name': 'Product Code', 'source_value': '%%c%%', 'gear_map': cls.gear_map}
        map_data_23 = {'target_name': 'Product Active', 'source_value': '%%b%%', 'gear_map': cls.gear_map}
        map_data_24 = {'target_name': 'Unit Price', 'source_value': '', 'gear_map': cls.gear_map}
        map_data_25 = {'target_name': 'Handler', 'source_value': '', 'gear_map': cls.gear_map}
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
        GearMapData.objects.create(**map_data_22)
        GearMapData.objects.create(**map_data_23)
        GearMapData.objects.create(**map_data_24)
        GearMapData.objects.create(**map_data_25)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.
        """
        self.source_controller = ZohoCRMController(
            self.plug_source.connection.related_connection, self.plug_source)

        self.target_controller = ZohoCRMController(
            self.plug_target.connection.related_connection, self.plug_target)

        # self.hook = {"b": "798-23-9610", "id": "PRODUCTID", "a": "Justin Williams", "c": "2011-10-23"}
        self.xml_data = '''
        <Products>
        <row no="1">
        <FL val="Vendor Name">Lauren Fitzpatrick</FL>
        <FL val="Product Name">516-84-4546</FL>
        <FL val="Product Owner">Lauren Fitzpatrick</FL>
        <FL val="Sales Start Date">1989-01-23</FL>
        <FL val="Support Start Date">516-84-4546</FL>
        <FL val="Sales End Date">Lauren Fitzpatrick</FL>
        <FL val="Product Code">1989-01-23</FL>
        <FL val="Product Active">516-84-4546</FL>
        </row>
        </Products>
       '''
        self.data = {
            'Vendor Name': 'Lauren Fitzpatrick',
            'Product Name': '516-84-4546',
            'Product Owner': 'Lauren Fitzpatrick',
            'Sales Start Date': '1989-01-23',
            'Support Start Date': '516-84-4546',
            'Sales End Date': 'Lauren Fitzpatrick',
            'Product Code': '1989-01-23',
            'Product Active': '516-84-4546',
        }


    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.
        """
        self.assertIsInstance(self.source_controller._connection_object, ZohoCRMConnection)
        self.assertIsInstance(self.target_controller._connection_object, ZohoCRMConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)
        self.assertNotEqual(self.source_controller._token, None)
        self.assertNotEqual(self.target_controller._token, None)

    def test_test_connection(self):
        """Testea la conexión"""
        result = self.source_controller.test_connection()
        self.assertTrue(result)

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection, self.plug_source)
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
        """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection, self.plug_source)
        count_store = StoredData.objects.filter(connection=self.source_connection, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        history_count = DownloadHistory.objects.all().count()
        self.assertNotEqual(count_store, 0)
        self.assertNotEqual(history_count, 0)

    def test_get_target_fields(self):
        """Verifica que retorne los campos de una tarea"""
        result = self.target_controller.get_target_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)


    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.target_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_get_action_specification_options(self):
        """Testea que retorne los action specification de manera correcta los canales de la cuenta"""
        action_specification_id = self.target_specification.id
        result = self.target_controller.get_action_specification_options(action_specification_id)
        _list = None
        for i in result:
            if i["id"] == os.environ.get("TEST_SOURCE_FEED"):
                _list = str(i["id"])
        self.assertIsInstance(result, tuple)
        self.assertEqual(_list, os.environ.get("TEST_SOURCE_FEED"))

    def test_send_stored_data(self):
        """Testea que el método retorne los paŕametros establecidos"""
        result1 = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                              self.plug_source, event=self.xml_data)
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

    def test_get_modules(self):
        """
        """
        result = self.source_controller.get_modules()
        self.assertIsNotNone(result)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['reason'], 'OK')
        self.assertEqual(str(result['status_code']), '200')

    def test_insert_records(self):
        """
        """
        result = self.target_controller.insert_records(data=self.data, module_id=os.environ.get('TEST_TARGET_FEED'))
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)

    def test_get_fields(self):
        """
        """
        result = self.source_controller.get_fields(module_id=os.environ.get('TEST_SOURCE_FEED'))
        self.assertIsInstance(result, list)

    def test_get_feeds(self):
        """
        """
        result = self.source_controller.get_feeds(module_name=os.environ.get('TEST_MODULE_NAME'))
        self.assertIsInstance(result, list)

    def test_get_module_name(self):
        """
        """
        result = self.source_controller.get_module_name(module_id=os.environ.get('TEST_SOURCE_FEED'))
        self.assertIsInstance(result, str)
        self.assertIsNotNone(result)