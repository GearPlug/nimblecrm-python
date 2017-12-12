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
import email

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
            "connector_id": ConnectorEnum.Gmail.value
        }
        cls.source_connection = Connection.objects.create(**connection)

        _credentials = json.loads(os.environ.get('TEST_GMAIL_CREDENTIALS_JSON'))

        _source_connection = {
            "connection": cls.source_connection,
            "name": "ConnectionTest Source",
            "credentials_json": _credentials,
            "history" : "",
        }
        cls.gmail_source_connection = GmailConnection.objects.create(**_source_connection)

        cls.target_connection = Connection.objects.create(**connection)

        _target_connection = {
            "connection": cls.target_connection,
            "name": "ConnectionTest Target",
            "credentials_json":_credentials,
            "history": "",
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

    def _get_dict_email(self):
        return {'To': 'grplugtest2@gmail.com', 'Id': '8745894722972', 'Content-Plain': 'R2VhcnBsdXRUZXN0MiBjb25uZWN0ZWQgdG8geW91ciBHb29nbGUgQWNjb3VudA0KDQoNCg0KSGkg\r\nRGllZ28sDQoNCkdlYXJwbHV0VGVzdDIgbm93IGhhcyBhY2Nlc3MgdG8geW91ciBHb29nbGUgQWNj\r\nb3VudCBncnBsdWd0ZXN0MkBnbWFpbC5jb20uDQoNCkdlYXJwbHV0VGVzdDIgY2FuOg0KDQogICAg\r\nLSBWaWV3IGFuZCBtb2RpZnkgYnV0IG5vdCBkZWxldGUgeW91ciBlbWFpbA0KDQoNCllvdSBzaG91\r\nbGQgb25seSBnaXZlIHRoaXMgYWNjZXNzIHRvIGFwcHMgeW91IHRydXN0LiBSZXZpZXcgb3IgcmVt\r\nb3ZlIGFwcHMNCmNvbm5lY3RlZCB0byB5b3VyIGFjY291bnQgYW55IHRpbWUgYXQgTXkgQWNjb3Vu\r\ndA0KPGh0dHBzOi8vbXlhY2NvdW50Lmdvb2dsZS5jb20vcGVybWlzc2lvbnM+Lg0KDQpMZWFybiBt\r\nb3JlIDxodHRwczovL3N1cHBvcnQuZ29vZ2xlLmNvbS9hY2NvdW50cy9hbnN3ZXIvMzQ2NjUyMT4g\r\nYWJvdXQgd2hhdA0KaXQgbWVhbnMgdG8gY29ubmVjdCBhbiBhcHAgdG8geW91ciBhY2NvdW50Lg0K\r\nVGhlIEdvb2dsZSBBY2NvdW50cyB0ZWFtDQoNCg0KDQpUaGlzIGVtYWlsIGNhbid0IHJlY2VpdmUg\r\ncmVwbGllcy4gRm9yIG1vcmUgaW5mb3JtYXRpb24sIHZpc2l0IHRoZSBHb29nbGUNCkFjY291bnRz\r\nIEhlbHAgQ2VudGVyIDxodHRwczovL3N1cHBvcnQuZ29vZ2xlLmNvbS9hY2NvdW50cy9hbnN3ZXIv\r\nMzQ2NjUyMT4uDQoNCg0KDQpZb3UgcmVjZWl2ZWQgdGhpcyBtYW5kYXRvcnkgZW1haWwgc2Vydmlj\r\nZSBhbm5vdW5jZW1lbnQgdG8gdXBkYXRlIHlvdSBhYm91dA0KaW1wb3J0YW50IGNoYW5nZXMgdG8g\r\neW91ciBHb29nbGUgcHJvZHVjdCBvciBhY2NvdW50Lg0KDQrCqSAyMDE3IEdvb2dsZSBJbmMuLCAx\r\nNjAwIEFtcGhpdGhlYXRyZSBQYXJrd2F5LCBNb3VudGFpbiBWaWV3LCBDQSA5NDA0MywgVVNBDQpl\r\ndDoxMjcNCg==', 'Message-Id': '<4CMu9kt6dlZK_rnWRyQ0AA@notifications.google.com>', 'Date': 'Tue, 12 Dec 2017 15:59:48 +0000 (UTC)', 'Content-Html': '<html lang=3D"en"><head><meta name=3D"format-detection" content=3D"date=3Dn=\r\no"/><meta name=3D"format-detection" content=3D"email=3Dno"/><style>.awl a {=\r\ncolor: #FFFFFF; text-decoration: none;}.abml a {color: #000000; font-family=\r\n: Roboto-Medium,Helvetica,Arial,sans-serif; font-weight: bold; text-decorat=\r\nion: none;}.afal a {color: #b0b0b0; text-decoration: none;}@media screen an=\r\nd (min-width: 600px) {.v2sp {padding: 6px 30px 0px;} .v2rsp {padding: 0px 1=\r\n0px;}}</style></head><body style=3D"margin: 0; padding: 0;" bgcolor=3D"#FFF=\r\nFFF"><table width=3D"100%" height=3D"100%" style=3D"min-width: 348px;" bord=\r\ner=3D"0" cellspacing=3D"0" cellpadding=3D"0"><tr height=3D"32px"></tr><tr a=\r\nlign=3D"center"><td width=3D"32px"></td><td><table border=3D"0" cellspacing=\r\n=3D"0" cellpadding=3D"0" style=3D"max-width: 600px;"><tr><td><table width=\r\n=3D"100%" border=3D"0" cellspacing=3D"0" cellpadding=3D"0"><tr><td align=3D=\r\n"left"><img width=3D"92" height=3D"32" src=3D"https://www.gstatic.com/accou=\r\nntalerts/email/googlelogo_color_188x64dp.png" style=3D"display: block; widt=\r\nh: 92px; height: 32px;"></td><td align=3D"right"><img width=3D"32" height=\r\n=3D"32" style=3D"display: block; width: 32px; height: 32px;" src=3D"https:/=\r\n/www.gstatic.com/accountalerts/email/keyhole.png"></td></tr></table></td></=\r\ntr><tr height=3D"16"></tr><tr><td><table bgcolor=3D"#4184F3" width=3D"100%"=\r\n border=3D"0" cellspacing=3D"0" cellpadding=3D"0" style=3D"min-width: 332px=\r\n; max-width: 600px; border: 1px solid #F0F0F0; border-bottom: 0; border-top=\r\n-left-radius: 3px; border-top-right-radius: 3px;"><tr><td height=3D"72px" c=\r\nolspan=3D"3"></td></tr><tr><td width=3D"32px"></td><td style=3D"font-family=\r\n: Roboto-Regular,Helvetica,Arial,sans-serif; font-size: 24px; color: #FFFFF=\r\nF; line-height: 1.25; min-width: 300px;"><a class=3D"awl" style=3D"text-dec=\r\noration: none; color: #FFFFFF;">GearplutTest2</a> connected to your Google&=\r\nnbsp;Account</td><td width=3D"32px"></td></tr><tr><td height=3D"18px" colsp=\r\nan=3D"3"></td></tr></table></td></tr><tr><td><table bgcolor=3D"#FAFAFA" wid=\r\nth=3D"100%" border=3D"0" cellspacing=3D"0" cellpadding=3D"0" style=3D"min-w=\r\nidth: 332px; max-width: 600px; border: 1px solid #F0F0F0; border-bottom: 1p=\r\nx solid #C0C0C0; border-top: 0; border-bottom-left-radius: 3px; border-bott=\r\nom-right-radius: 3px;"><tr height=3D"16px"><td width=3D"32px" rowspan=3D"3"=\r\n></td><td></td><td width=3D"32px" rowspan=3D"3"></td></tr><tr><td><table st=\r\nyle=3D"min-width: 300px;" border=3D"0" cellspacing=3D"0" cellpadding=3D"0">=\r\n<tr><td style=3D"font-family: Roboto-Regular,Helvetica,Arial,sans-serif; fo=\r\nnt-size: 13px; color: #202020; line-height: 1.5;padding-bottom: 4px;">Hi Di=\r\nego,</td></tr><tr><td style=3D"font-family: Roboto-Regular,Helvetica,Arial,=\r\nsans-serif; font-size: 13px; color: #202020; line-height: 1.5;padding: 4px =\r\n0;"><br><a class=3D"abml" style=3D"font-family: Roboto-Medium,Helvetica,Ari=\r\nal,sans-serif; font-weight: bold;text-decoration: none; color: #000000;">Ge=\r\narplutTest2</a> now has access to your Google Account <a class=3D"abml" sty=\r\nle=3D"font-family: Roboto-Medium,Helvetica,Arial,sans-serif; font-weight: b=\r\nold;text-decoration: none; color: #000000;">grplugtest2@gmail.com</a>.<br><=\r\nbr><a class=3D"abml" style=3D"font-family: Roboto-Medium,Helvetica,Arial,sa=\r\nns-serif; font-weight: bold;text-decoration: none; color: #000000;">Gearplu=\r\ntTest2</a> can:<ul style=3D"margin: 0;"><li>View and modify but not delete =\r\nyour email</li></ul><br>You should only give this access to apps you trust.=\r\n Review or remove apps connected to your account any time at <a href=3D"htt=\r\nps://myaccount.google.com/permissions" style=3D"text-decoration: none; colo=\r\nr: #4285F4;" target=3D"_blank">My Account</a>.<br><br><a href=3D"https://su=\r\npport.google.com/accounts/answer/3466521" style=3D"text-decoration: none; c=\r\nolor: #4285F4;" target=3D"_blank">Learn more</a> about what it means to con=\r\nnect an app to your account.</td></tr><tr><td style=3D"font-family: Roboto-=\r\nRegular,Helvetica,Arial,sans-serif; font-size: 13px; color: #202020; line-h=\r\neight: 1.5; padding-top: 28px;">The Google Accounts team</td></tr><tr heigh=\r\nt=3D"16px"></tr><tr><td><table style=3D"font-family: Roboto-Regular,Helveti=\r\nca,Arial,sans-serif; font-size: 12px; color: #B9B9B9; line-height: 1.5;"><t=\r\nr><td>This email can\'t receive replies. For more information, visit the <a =\r\nhref=3D"https://support.google.com/accounts/answer/3466521" data-meta-key=\r\n=3D"help" style=3D"text-decoration: none; color: #4285F4;" target=3D"_blank=\r\n">Google Accounts Help Center</a>.</td></tr></table></td></tr></table></td>=\r\n</tr><tr height=3D"32px"></tr></table></td></tr><tr height=3D"16"></tr><tr>=\r\n<td style=3D"max-width: 600px; font-family: Roboto-Regular,Helvetica,Arial,=\r\nsans-serif; font-size: 10px; color: #BCBCBC; line-height: 1.5;"><tr><td><ta=\r\nble style=3D"font-family: Roboto-Regular,Helvetica,Arial,sans-serif; font-s=\r\nize: 10px; color: #666666; line-height: 18px; padding-bottom: 10px"><tr><td=\r\n>You received this mandatory email service announcement to update you about=\r\n important changes to your Google product or account.</td></tr><tr height=\r\n=3D"6px"></tr><tr><td><div style=3D"direction: ltr; text-align: left">&copy=\r\n; 2017 Google Inc., 1600 Amphitheatre Parkway, Mountain View, CA 94043, USA=\r\n</div><div style=3D"display: none !important; mso-hide:all; max-height:0px;=\r\n max-width:0px;">et:127</div></td></tr></table></td></tr></td></tr></table>=\r\n</td><td width=3D"32px"></td></tr><tr height=3D"32px"></tr></table></body><=\r\n/html>', 'From': 'Google <no-reply@accounts.google.com>', 'Subject': 'GearplutTest2 connected to your Google Account'}

    def _get_fields(self):
        return [{'name': 'to', 'label':'To', 'type': 'varchar', 'required': True},
                {'name': 'sender', 'label':'Sender','type': 'varchar', 'required': True},
                {'name': 'subject', 'label':'Subject', 'type': 'varchar', 'required': True},
                {'name': 'msgHtml', 'label': 'Message', 'type': 'varchar', 'required': True},
               ]
    def test_controller(self):
        """
        Comprueba que los atributos del controlador esten instanciados
        """
        self.assertIsInstance(self.source_controller._connection_object, GmailConnection)
        self.assertIsInstance(self.target_controller._connection_object, GmailConnection)
        self.assertIsInstance(self.source_controller._plug, Plug)
        self.assertIsInstance(self.target_controller._plug, Plug)
        self.assertTrue(self.source_controller._credential)
        self.assertTrue(self.target_controller._credential)
        self.assertTrue(self.source_controller._service)
        self.assertTrue(self.target_controller._service)

    def test_test_connection(self):
        """
        Comprueba que la conexión sea valida
        """
        source_result = self.source_controller.test_connection()
        target_result = self.target_controller.test_connection()
        self.assertTrue(source_result)
        self.assertTrue(target_result)

    def test_create_webhook(self):
        """Testea que se cree un webhook en la aplicación y que se cree en la tabla Webhook, al final se borra el
        webhook de la aplicación"""
        self.source_controller.create_webhook()
        count_webhook = Webhook.objects.filter(plug=self.source_plug).count()
        self.assertEqual(count_webhook, 1)

    def test_get_profile(self):
        result = self.source_controller.get_profile()
        self.assertIn('emailAddress', result)
        self.assertEqual(result['emailAddress'], os.environ.get('TEST_GMAIL_EMAIL'))

    def test_get_action_specification_options(self):
        action_specification_id = self.source_specification.id
        result = self.source_controller.get_action_specification_options(action_specification_id)
        self.assertIsInstance(result, tuple)
        self.assertEqual(result[0]['id'], os.environ.get('TEST_GMAIL_EMAIL'))

    def test_get_history(self):
        self.source_controller.create_webhook()
        _connection = GmailConnection.objects.first()
        history_id = _connection.history
        self.target_controller.send_message("grplugtest1@gmail.com", os.environ.get('TEST_GMAIL_EMAIL'), "prueba", "mensaje de prueba")
        result = self.source_controller.get_history(history_id)
        self.assertIn('historyId', result)
        self.assertIn('history', result)
        self.assertIsInstance(result['history'], list)

    def test_get_message(self):
        self.source_controller.create_webhook()
        _connection = GmailConnection.objects.first()
        history_id = _connection.history
        self.target_controller.send_message("grplugtest1@gmail.com", os.environ.get('TEST_GMAIL_EMAIL'), "prueba",
                                            "mensaje de prueba")
        result_history = self.source_controller.get_history(history_id)
        _message_id = result_history['history'][0]['messagesAdded'][0]['message']['id']
        result_message = self.source_controller.get_message(message_id=_message_id)
        self.assertIsInstance(result_message, email.message.Message)

    def test_download_source_data(self):
        "Simula un dato de entrada y verifica que esté se cree en las tablas DownloadHistory y StoreData"
        self.source_controller.download_source_data(self.source_plug.connection.related_connection, self.source_plug, message=self._get_dict_email())
        count_store = StoredData.objects.filter(connection=self.source_connection, plug=self.source_plug).count()
        count_history = DownloadHistory.objects.all().count()
        self.assertNotEqual(count_store, 0)
        self.assertNotEqual(count_history, 0)

    def test_download_to_store_data(self):
        """Verifica que retorne una lista de acuerdo a:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        """
        result = self.source_controller.download_to_stored_data(self.source_plug.connection.related_connection, self.source_plug, message=self._get_dict_email())
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
        """Verifica los fields de un contacto"""
        result = self.target_controller.get_target_fields()
        self.assertEqual(result, self._get_fields())

    def test_get_mapping_fields(self):
        """Testea que retorne los Mapping Fields de manera correcta"""
        result = self.target_controller.get_mapping_fields()
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[0], MapField)

    def test_send_stored_data(self):
        """ Verifica que se cree un contacto y que el métod send_store_data retorne una lista de acuerdo a:
                {'data': {(%dict del metodo 'get_dict_with_source_data')},
                 'response': (%mensaje del resultado),
                 'sent': True|False,
                 'identifier': (%identificador del dato enviado. Ej: ID.)
                }
                Al final se borra el contacto de la aplicación.
                """
        _data = {'to':'grplugtest1@gmail.com', 'msgHtml':'7mensaje', 'sender': 'grplugtest2@gmail.com', 'subject': 'mensaje7'}
        data_list = [OrderedDict(_data)]
        result = self.target_controller.send_stored_data(data_list)
        self.assertIsInstance(result, list)
        self.assertIsInstance(result[-1], dict)
        self.assertIn('data', result[-1])
        self.assertIn('response', result[-1])
        self.assertIn('sent', result[-1])
        self.assertIn('identifier', result[-1])
        self.assertIsInstance(result[-1]['data'], dict)
        self.assertIsInstance(result[-1]['sent'], bool)
        self.assertEqual(result[-1]['data'], dict(data_list[0]))

    def test_send_target_data(self):
        """Verifica que se cree el registro ingresado en la tabla Sendstoredata, al final se borra
        el contacto de la aplicación"""
        _source =  [{'id': '8', 'data': {'id': '8', 'subject': 'mensaje8', 'sender': 'grplugtest2@gmail.com', 'message': '8 mensaje', 'email': 'grplugtest1@gmail.com'}}]
        _target_fields = {'to':'%%email%%', 'msgHtml':'%%message%%','sender':'%%sender%%','subject':'%%subject%%'}
        _target = OrderedDict(_target_fields)
        self.target_controller.send_target_data(source_data=_source, target_fields=_target)
        count_history = SendHistory.objects.all().count()
        self.assertNotEqual(count_history, 0)

    def test_create_message(self):
        result = self.target_controller.create_message("grplugtest1@gmail.com", os.environ.get('TEST_GMAIL_EMAIL'), "prueba", "mensaje de prueba")
        self.assertIn('raw', result)
        self.assertIsInstance(result, dict)

    def test_send_message_internal(self):
        _message = self.target_controller.create_message("grplugtest1@gmail.com", os.environ.get('TEST_GMAIL_EMAIL'),
                                                       "prueba", "mensaje de prueba")
        result = self.target_controller.send_message_internal("me", _message)
        self.assertIsInstance(result, dict)
        self.assertIn("id", result)
        self.assertIn("threadId", result)
        self.assertIn("labelIds", result)

    def test_send_message_internal(self):
        result = self.target_controller.send_message("grplugtest1@gmail.com", os.environ.get('TEST_GMAIL_EMAIL'),
                                                       "prueba", "mensaje de prueba")
        self.assertIsInstance(result, dict)
        self.assertIn("id", result)
        self.assertIn("threadId", result)
        self.assertIn("labelIds", result)