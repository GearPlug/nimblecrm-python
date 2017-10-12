import os
from django.test import TestCase, Client
from django.contrib.auth.models import User
from apps.gp.models import Connection, BitbucketConnection, Plug, Action, \
    ActionSpecification, PlugActionSpecification, Gear, StoredData, Webhook
from apps.gp.controllers.repository import BitbucketController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from collections import OrderedDict
from apps.history.models import DownloadHistory

class BitbucketControllerTestCases(TestCase):
    """
    TEST_BITBUCKET_USER : String: Usuario
    TEST_BITBUCKET_PASSWORD : String: Contraseña
    TEST_BITBUCKET_REPOSITORY : String: ID de un repositorio existente
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(username='lrubiano@grplug.com',
                                       email='lrubiano@grplug.com',
                                       password='Prueba#2017')
        _dict_source_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Bitbucket.value
        }
        cls.source_connection = Connection.objects.create(**_dict_source_connection)

        _dict_target_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.Bitbucket.value
        }
        cls.target_connection = Connection.objects.create(**_dict_target_connection)
        _dict_bitbucket_source_connection = {
            'connection': cls.source_connection,
            'name': 'ConnectionTest',
            'connection_user': os.environ.get('TEST_BITBUCKET_USER'),
            'connection_password': os.environ.get('TEST_BITBUCKET_PASSWORD'),
        }
        cls.bitbucket_source_connection = BitbucketConnection.objects.create(**_dict_bitbucket_source_connection)
        _dict_bitbucket_target_connection = {
            'connection': cls.target_connection,
            'connection_user': os.environ.get('TEST_BITBUCKET_USER'),
            'connection_password': os.environ.get('TEST_BITBUCKET_PASSWORD'),
        }
        cls.bitbucket_target_connection = BitbucketConnection.objects.create(**_dict_bitbucket_target_connection)

        source_action = Action.objects.get(connector_id=ConnectorEnum.Bitbucket.value,
                                    action_type='source',
                                    name='new issue created',
                                    is_active=True)

        target_action = Action.objects.get(connector_id=ConnectorEnum.Bitbucket.value,
                                           action_type='target',
                                           name='create issue',
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
                                                         name='repository')

        cls.target_specification = ActionSpecification.objects.get(action=target_action,
                                                               name='repository')

        _dict_source_specification = {
            'plug': cls.plug_source,
            'action_specification': cls.source_specification,
            'value': os.environ.get('TEST_BITBUCKET_REPOSITORY')
        }
        PlugActionSpecification.objects.create(**_dict_source_specification)

        _dict_target_specification = {
            'plug': cls.plug_target,
            'action_specification': cls.target_specification,
            'value': os.environ.get('TEST_BITBUCKET_REPOSITORY')
        }
        PlugActionSpecification.objects.create(**_dict_target_specification)

        _dict_gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**_dict_gear)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.
        """
        self.source_controller = BitbucketController(
            self.plug_source.connection.related_connection, self.plug_source)

        self.target_controller = BitbucketController(
            self.plug_target.connection.related_connection, self.plug_target)

        self.hook = {'issue':
                         {'assignee': None,
                         'component': None,
                         'content': {'html': '', 'markup': 'markdown', 'raw': ''},
                         'created_on': '2017-10-09T18:35:25.476557+00:00',
                         'edited_on': None,
                         'id': 18,
                         'kind': 'bug',
                         'links': {'attachments': {'href': 'https://api.bitbucket.org/2.0/repositories/lyrubiano10/myrepository/issues/18/attachments'},
                                   'comments': {'href': 'https://api.bitbucket.org/2.0/repositories/lyrubiano10/myrepository/issues/18/comments'},
                                   'html': {'href': 'https://bitbucket.org/lyrubiano10/myrepository/issues/18/jjjjj'},
                                   'self': {'href': 'https://api.bitbucket.org/2.0/repositories/lyrubiano10/myrepository/issues/18'},
                                   'vote': {'href': 'https://api.bitbucket.org/2.0/repositories/lyrubiano10/myrepository/issues/18/vote'},
                                   'watch': {'href': 'https://api.bitbucket.org/2.0/repositories/lyrubiano10/myrepository/issues/18/watch'}},
                         'milestone': None,
                         'priority': 'major',
                         'reporter': {'display_name': 'Lelia Rubiano',
                                      'links': {'avatar': {'href': 'https://bitbucket.org/account/lyrubiano10/avatar/32/'},
                                                'html': {'href': 'https://bitbucket.org/lyrubiano10/'},
                                                'self': {'href': 'https://api.bitbucket.org/2.0/users/lyrubiano10'}},
                                      'type': 'user',
                                      'username': 'lyrubiano10',
                                      'uuid': '{df9a00c3-50e7-42a7-a41d-a465d122fc2e}'},
                         'state': 'new',
                         'title': 'jjjjj',
                         'type': 'issue',
                         'updated_on': '2017-10-09T18:35:25.476557+00:00',
                         'version': None,
                         'votes': 0,
                         'watches': 1}}

        self.data_send = OrderedDict({'priority':'trivial','status':'new','title':'try', 'kind':'bug'})

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.
        """
        self.assertIsInstance(self.source_controller._connection_object, BitbucketConnection)
        self.assertIsInstance(self.target_controller._connection_object, BitbucketConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)
        self.assertNotEqual(self.source_controller._connection, None)
        self.assertNotEqual(self.target_controller._connection, None)

    def test_test_connection(self):
        """
        Verifica que la conexión este establecida
        """
        result = self.source_controller.test_connection()
        self.assertNotEqual(result, None)

    def test_has_webhook(self):
        """Verifica que retorne True"""
        result = self.source_controller.has_webhook()
        self.assertTrue(result)

    def test_get_header(self):
        """Verifica que retorne las credenciales esperadas"""
        result = self.source_controller._get_header()
        self.assertIn('Accept', result)
        self.assertIn('Authorization', result)
        self.assertIsInstance(result, dict)

    def test_get_repositories(self):
        """Verifica que retorne la lista de repositorios, se verifica mediante la variable TEST_BITBUCKET_REPOSITORY, el
        cual se debe retornar en la lista"""
        result = self.source_controller.get_repositories()
        repository = ""
        for r in result:
            if r['uuid'] == os.environ.get('TEST_BITBUCKET_REPOSITORY'):
                repository = r['uuid']
        self.assertEqual(repository, os.environ.get('TEST_BITBUCKET_REPOSITORY'))

    def test_get_repository_name(self):
        """Testea que devuelva el nombre de un repositorio"""
        result = self.source_controller.get_repository_name(os.environ.get('TEST_BITBUCKET_REPOSITORY'))
        self.assertNotEqual(result, "")

    def test_create_webhook(self):
        """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
        webhook de la aplicación"""
        result_create = self.source_controller.create_webhook()
        count_webhook= Webhook.objects.filter(plug=self.plug_source).count()
        webhook = Webhook.objects.last()
        result_view = self.source_controller.view_webhook(webhook.generated_id)
        self.source_controller.delete_webhook(webhook.generated_id)
        self.assertEqual(count_webhook , 1)
        self.assertTrue(result_create)

    def test_delete_webhook(self):
        """Testea que se borre un webhook de la aplicación, primero se crea un webhook"""
        self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        self.source_controller.delete_webhook(webhook.generated_id)
        result_view = self.source_controller.view_webhook(webhook.generated_id)
        self.assertEqual(result_view['type'], 'error')

    def test_view_webhook(self):
        """Testa que se mire los parámetros de un webhook, se crea un webhook y al final se borra"""
        self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        result_view = self.source_controller.view_webhook(webhook.generated_id)
        self.assertEqual(result_view['uuid'], webhook.generated_id)
        self.source_controller.delete_webhook(webhook.generated_id)

    def test_do_webhook_process(self):
        """Simula un dato de entrada (self.hook), se crea un webhook y se verifica que retorne
        un status code =200, al final se borra el webhook"""
        self.source_controller.create_webhook()
        webhook = Webhook.objects.last()
        result = self.source_controller.do_webhook_process(body=self.hook, webhook_id=webhook.id)
        self.assertEqual(result.status_code, 200)
        self.source_controller.delete_webhook(webhook.generated_id)

    def test_download_source_data(self):
        """Simula un dato de entrada (self.hook) y se verifica que este dato se cree en las tablas DownloadHistory y StoreData"""
        count_data = len(self.hook['issue'])
        result = self.source_controller.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source, issue=self.hook['issue'])
        count_store = StoredData.objects.filter(connection=self.source_connection, plug=self.plug_source).count()
        history = DownloadHistory.objects.last()
        self.assertEqual(count_store, count_data)
        data = str(self.hook['issue'])
        self.assertEqual(history.identifier, str({'name': 'id', 'value': self.hook['issue']['id']}))

    def test_download_to_store_data(self):
        """Simula un dato de entrada por webhook (self.hook), y se verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.source_controller.download_to_stored_data(self.plug_source.connection.related_connection, self.plug_source,
                                                         issue=self.hook['issue'])
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

    def test_get_components(self):
        """Testea que el resultado sea una lsita"""
        result = self.target_controller.get_components()
        self.assertIsInstance(result, list)

    def test_get_versions(self):
        """Testea que el resultado sea una lsita"""
        result = self.target_controller.get_versions()
        self.assertIsInstance(result, list)

    def test_get_milestones(self):
        """Testea que el resultado sea una lsita"""
        result = self.target_controller.get_milestones()
        self.assertIsInstance(result, list)

    def test_meta(self):
        """Testea los fields del connector"""
        result = self.target_controller.get_meta()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], dict)

    def test_request(self):
        """Testea que se haga un request con una url determinada"""
        url = '/2.0/repositories/{0}'.format(self.source_controller._user)
        result = self.source_controller._request(url)
        self.assertIn('values', result)

    def test_get_target_fiels(self):
        """Testea que retorne los campos de un contacto"""
        result = self.target_controller.get_target_fields()
        target_fields = self.target_controller.get_meta()
        self.assertEqual(result, target_fields)

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.target_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_create_issue(self): #el mismo test para view_issue
        """Testea que se cree un issue"""
        result_create = self.target_controller.create_issue(self.data_send)
        result_view = self.target_controller.view_issue(result_create[1]['local_id'])
        self.assertEqual(result_create[1]['local_id'], result_view['id'])

    def test_send_stored_data(self):
        """Testea que el método retorne los paŕametros establecidos"""
        data_list = [self.data_send]
        result = self.target_controller.send_stored_data(data_list)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)
        self.assertIn('data', result[-1])
        self.assertIn('response', result[-1])
        self.assertIn('sent', result[-1])
        self.assertIn('identifier', result[-1])
        self.assertIsInstance(result[-1]['data'], dict)
        self.assertIsInstance(result[-1]['response'], str)
        self.assertIsInstance(result[-1]['sent'], bool)
        self.assertEqual(result[-1]['data'], dict(data_list[0]))
        result_view = self.target_controller.view_issue(int(result[-1]['identifier']))
        self.assertEqual(result_view['id'], result[-1]['identifier'])

