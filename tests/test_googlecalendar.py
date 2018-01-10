from apps.gp.controllers.ofimatic import GoogleCalendarController
from apps.gp.models import Connection, ConnectorEnum, Action, Plug, ActionSpecification, PlugActionSpecification, \
    GoogleCalendarConnection, StoredData, Gear, Webhook, GearMap, GearMapData
from apps.history.models import DownloadHistory, SendHistory
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import HttpResponse
from django.test import TestCase, Client
from collections import OrderedDict
import json
import os
import datetime


class GoogleCalendarControllerTestCases(TestCase):
    """Casos de prueba del controlador Google Forms.

        Variables de entorno:
            TEST_GOOGLECALENDAR_CREDENTIALS: String: Token generado a partir de oAuth.
            TEST_GOOGLECALENDAR_CALENDAR: String: Nombre del calendario.
    """
    fixtures = ['gp_base.json']

    @classmethod
    def setUpTestData(cls):
        """Crea la base de datos y genera datos falsos en las tablas respectivas.

        """
        cls.user = User.objects.create(username='test', email='lyrubiano5@gmail.com', password='Prueba#2017')
        _dict_source_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.GoogleCalendar.value
        }
        cls.connection_source = Connection.objects.create(**_dict_source_connection)

        _dict_target_connection = {
            'user': cls.user,
            'connector_id': ConnectorEnum.GoogleCalendar.value
        }
        cls.connection_target = Connection.objects.create(**_dict_target_connection)

        _dict_googlecalendar_source_connection = {
            'connection': cls.connection_source,
            'name': 'ConnectionTest Source',
            'credentials_json': json.loads(os.environ.get('TEST_GOOGLECALENDAR_CREDENTIALS')),
        }
        cls.googlecalendar_source_connection = GoogleCalendarConnection.objects.create(
            **_dict_googlecalendar_source_connection)

        _dict_googlecalendar_target_connection = {
            'connection': cls.connection_target,
            'name': 'ConnectionTest Target',
            'credentials_json': json.loads(os.environ.get('TEST_GOOGLECALENDAR_CREDENTIALS')),
        }
        cls.googlecalendar_target_connection = GoogleCalendarConnection.objects.create(
            **_dict_googlecalendar_target_connection)

        action_source = Action.objects.get(connector_id=ConnectorEnum.GoogleCalendar.value, action_type='source',
                                           name='new event', is_active=True)
        action_target = Action.objects.get(connector_id=ConnectorEnum.GoogleCalendar.value, action_type='target',
                                           name='create event', is_active=True)

        googlecalendar_plug_source = {
            'name': 'PlugTest Source',
            'connection': cls.connection_source,
            'action': action_source,
            'plug_type': 'source',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_source = Plug.objects.create(**googlecalendar_plug_source)

        googlecalendar_plug_target = {
            'name': 'PlugTest Target',
            'connection': cls.connection_target,
            'action': action_target,
            'plug_type': 'target',
            'user': cls.user,
            'is_active': True

        }
        cls.plug_target = Plug.objects.create(**googlecalendar_plug_target)

        cls.source_specification = ActionSpecification.objects.get(action=action_source, name='calendar')
        cls.target_specification = ActionSpecification.objects.get(action=action_target, name='calendar')

        action_specification1 = {
            'plug': cls.plug_source,
            'action_specification': cls.source_specification,
            'value': os.environ.get('TEST_GOOGLECALENDAR_CALENDAR')
        }
        PlugActionSpecification.objects.create(**action_specification1)

        action_specification1 = {
            'plug': cls.plug_target,
            'action_specification': cls.target_specification,
            'value': os.environ.get('TEST_GOOGLECALENDAR_CALENDAR')
        }
        PlugActionSpecification.objects.create(**action_specification1)

        gear = {
            'name': 'Gear 1',
            'user': cls.user,
            'source': cls.plug_source,
            'target': cls.plug_target,
            'is_active': True
        }
        cls.gear = Gear.objects.create(**gear)
        cls.gear_map = GearMap.objects.create(gear=cls.gear)

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(hours=1)
        map_data_1 = {'target_name': 'summary', 'source_value': '%%summary%%', 'gear_map': cls.gear_map}
        map_data_2 = {'target_name': 'start_dateTime', 'source_value': start_time, 'gear_map': cls.gear_map}
        map_data_3 = {'target_name': 'end_dateTime', 'source_value': end_time, 'gear_map': cls.gear_map}
        map_data_4 = {'target_name': 'start_timeZone', 'source_value': 'America/Bogota', 'gear_map': cls.gear_map}
        map_data_5 = {'target_name': 'end_timeZone', 'source_value': 'America/Bogota', 'gear_map': cls.gear_map}
        GearMapData.objects.create(**map_data_1)
        GearMapData.objects.create(**map_data_2)
        GearMapData.objects.create(**map_data_3)
        GearMapData.objects.create(**map_data_4)
        GearMapData.objects.create(**map_data_5)

    def setUp(self):
        """Instancia el controlador e inicializa variables de webhooks en caso de usarlos.

        """
        self.controller_source = GoogleCalendarController(self.plug_source.connection.related_connection,
                                                          self.plug_source)
        self.controller_target = GoogleCalendarController(self.plug_target.connection.related_connection,
                                                          self.plug_target)

        self.events = [{'status': 'confirmed', 'htmlLink': 'https://www.google.com/calendar/event?eid=M21sZjFtMGtjOXFsMm10MWZpNDQ2MjBmdTQgZ3JwbHVnLmNvbV9yMzI5N3VwZ2JqbjlndGQ3b2JpdDA3dXEzMEBn', 'hangoutLink': 'https://plus.google.com/hangouts/_/grplug.com/testing?hceid=Z3JwbHVnLmNvbV9yMzI5N3VwZ2JqbjlndGQ3b2JpdDA3dXEzMEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t.3mlf1m0kc9ql2mt1fi44620fu4', 'sequence': 0, 'kind': 'calendar#event', 'creator': {'email': 'mferrer@grplug.com'}, 'start': {'dateTime': '2018-01-09T15:00:00-05:00'}, 'etag': '"3031053784864000"', 'updated': '2018-01-09T19:41:32.432Z', 'end': {'dateTime': '2018-01-09T16:00:00-05:00'}, 'organizer': {'self': True, 'displayName': 'Unittest', 'email': 'grplug.com_r3297upgbjn9gtd7obit07uq30@group.calendar.google.com'}, 'iCalUID': '3mlf1m0kc9ql2mt1fi44620fu4@google.com', 'id': '3mlf1m0kc9ql2mt1fi44620fu4', 'summary': 'Testing', 'reminders': {'useDefault': True}, 'created': '2018-01-09T19:41:32.000Z', 'conferenceData': {'createRequest': {'requestId': 'u0egdrbal3nq8f01pllcev2ejg', 'status': {'statusCode': 'success'}, 'conferenceSolutionKey': {'type': 'eventNamedHangout'}}, 'signature': 'ANJzi0T8iFvcsEiLYhShE8f0jfXh', 'conferenceId': 'testing', 'entryPoints': [{'entryPointType': 'video', 'uri': 'https://plus.google.com/hangouts/_/grplug.com/testing?hceid=Z3JwbHVnLmNvbV9yMzI5N3VwZ2JqbjlndGQ3b2JpdDA3dXEzMEBncm91cC5jYWxlbmRhci5nb29nbGUuY29t.3mlf1m0kc9ql2mt1fi44620fu4', 'label': 'testing'}], 'conferenceSolution': {'iconUri': 'https://lh5.googleusercontent.com/proxy/9vT2XwMHPzrIcW56Ic3FX6_OSYvrjHEwOUYOmA0eMoR-_sY59k4mQMd0JnqCp8GCOmqimFKP3vSeFaIe4k5MewpEcCuK6PXlB2Z4AKTMV78OB_CJqXHrrkAO-yf5FYJsiaTBwjUP9cU0lRlP-HPC2w', 'name': 'Google Hangouts', 'key': {'type': 'eventNamedHangout'}}}}]

    def test_controller(self):
        """Comprueba los atributos del controlador estén instanciados.

        """
        self.assertIsInstance(self.controller_source._connection_object, GoogleCalendarConnection)
        self.assertIsInstance(self.controller_source._plug, Plug)
        self.assertTrue(self.controller_source._credential)

        self.assertIsInstance(self.controller_target._connection_object, GoogleCalendarConnection)
        self.assertIsInstance(self.controller_target._plug, Plug)
        self.assertTrue(self.controller_target._credential)

    def test_test_connection(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result_source = self.controller_source.test_connection()
        self.assertTrue(result_source)

    def test_calendar_list(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_calendar_list()
        self.assertIsInstance(result, tuple)
        self.assertTrue(result)

    def test_events(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_events()
        self.assertIsInstance(result, list)
        self.assertTrue(result)

    def test_get_target_fields(self):
        """Comprueba que la llamada al metodo devuelva el tipo de dato esperado.

        """
        result = self.controller_source.get_target_fields()
        self.assertIsInstance(result, list)
        self.assertTrue(result)

    def test_download_to_stored_data(self):
        """Comprueba que la llamada al metodo devuelva un diccionario y la existencia de los atributos necesarios y
        su respectivo tipo de dato almacenado como valor.

        """
        result = self.controller_source.download_to_stored_data(self.plug_source.connection.related_connection,
                                                                self.plug_source, events=self.events)
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
        result = self.controller_source.download_source_data(self.plug_source.connection.related_connection,
                                                             self.plug_source, events=self.events)

        qs = StoredData.objects.order_by('object_id').values_list('object_id', flat=True).distinct()
        for row in qs:
            count = DownloadHistory.objects.filter(identifier={'name': 'id', 'value': row}).count()
            self.assertGreater(count, 0)

    def test_do_webhook_process(self):
        """Comprueba que la llamada al metodo devuelva un HTTP Response con un Status Code específico y que
        como resultado del proceso haya data guardada en StoredData.

        """
        _dict = {
            'name': 'calendar',
            'plug': self.plug_source,
            'url': settings.WEBHOOK_HOST,
            'expiration': '',
            'generated_id': '1',
            'is_active': True
        }
        webhook = Webhook.objects.create(**_dict)
        result = self.controller_source.do_webhook_process(POST=True, webhook_id=webhook.id)
        self.assertIsInstance(result, HttpResponse)
        self.assertEqual(result.status_code, 200)

        count = StoredData.objects.count()
        self.assertNotEqual(count, 0)

    def test_send_stored_data(self):
        """Guarda datos en StoredData y luego los envía la data mapeada al servidor CRM, luego comprueba de que
               el valor devuelto sea una lista además de comprobar que esté guardando registros en SendHistory.

        """
        result1 = self.controller_source.download_source_data(self.plug_source.connection.related_connection,
                                                              self.plug_source, events=self.events)
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
        entries = self.controller_target.send_target_data(source_data, target_fields, is_first=is_first)
        self.assertIsInstance(entries, list)

        for object_id in entries:
            count = SendHistory.objects.filter(identifier=object_id).count()
            self.assertGreater(count, 0)
