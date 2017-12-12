from apps.gp.controllers.base import BaseController, GoogleBaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.map import MapField
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Webhook, StoredData, ActionSpecification, Plug
from django.http import HttpResponse
from django.db.models import Q
from django.conf import settings
from django.urls import reverse
from utils.smtp_sender import smtpSender as SMTPClient
from oauth2client import client as GoogleClient
from apiclient import discovery, errors
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import httplib2
import base64
from email import message_from_bytes


class GmailController(GoogleBaseController):
    _credential = None
    _service = None

    def __init__(self, connection=None, plug=None, **kwargs):
        GoogleBaseController.__init__(self, connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        credentials_json = None
        super(GmailController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                credentials_json = self._connection_object.credentials_json
            except Exception as e:
                print(e)
                credentials_json = None
        if credentials_json is not None:
            self._credential = GoogleClient.OAuth2Credentials.from_json(json.dumps(credentials_json))
            self._service = discovery.build('gmail', 'v1', http=self._credential.authorize(httplib2.Http()))

    def test_connection(self):
        try:
            self.get_profile()
        except:
            try:
                self._refresh_token()
            except GoogleClient.HttpAccessTokenRefreshError:
                self._report_broken_token()
                return None
        return self._credential is not None

    def create_webhook(self):
        """
        Para que el res_watch funcione se necesita agregar a la cuenta gmail-api-push@system.gserviceaccount.com, con el rol PUB/SUB editor.
        Adicionalmente se debe crear una susbscripción en la cual se agrega la url del webhook {host}/webhook/gmail/0
        """
        action = self._plug.action.name
        if action.lower() == 'new email':
            # Creacion de Webhook
            webhook = Webhook.objects.create(name='gmail', plug=self._plug, url='')
            request = {
                'labelIds': ['INBOX'],
                'topicName': settings.GMAIL_TOPIC_NAME,
                'name': 'webhook'
            }
            try:
                res_watch = self._service.users().watch(userId='me', body=request).execute()
            except:
                res_watch is None
            if res_watch is not None:
                _profile = self.get_profile()
                self._connection_object.history = self.get_profile()['historyId']
                self._connection_object.save(update_fields=['history'])
                webhook.url = settings.WEBHOOK_HOST + reverse('home:webhook',
                                                              kwargs={'connector': 'gmail', 'webhook_id': 0})
                webhook.generated_id = self._plug.id
                webhook.is_active = True
                webhook.expiration = res_watch['expiration']
                webhook.save(update_fields=['url', 'generated_id', 'is_active', 'expiration'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted'])
            return True
        return False

    def download_to_stored_data(self, connection_object=None, plug=None, message=None, **kwargs):
        message_stored_data = []
        if message is not None:
            _id = message['Id']
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=_id)
            if not q.exists():
                message_stored_data = []
                for k, v in message.items():
                    message_stored_data.append(
                        StoredData(connection=connection_object.connection, plug=plug, name=k, value=v, object_id=_id))
            if message_stored_data:
                for msg in message_stored_data:
                    try:
                        msg.save()
                        is_stored = True
                    except Exception as e:
                        is_stored = False
                        print(e)
            result_list = [{'raw':message, 'is_stored':is_stored, 'identifier':{'name':'Id', 'value':_id}}]
            return {'downloaded_data':result_list, 'last_source_record':_id}
        return False

    def get_target_fields(self, **kwargs):
        return [{'name': 'to', 'label':'To', 'type': 'varchar', 'required': True},
                {'name': 'sender', 'label':'Sender','type': 'varchar', 'required': True},
                {'name': 'subject', 'label':'Subject', 'type': 'varchar', 'required': True},
                {'name': 'msgHtml', 'label': 'Message', 'type': 'varchar', 'required': True},
               ]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Gmail) for f in fields]

    def send_stored_data(self, data_list):
        obj_list = []
        for item in data_list:
            email = self.send_message(**item)
            if email['id']:
                _identifier = email['id']
                _sent = True
            else:
                _identifier = ""
                _sent = False
            obj_list.append({'data':dict(item), 'response': email['labelIds'], 'sent': _sent, 'identifier':_identifier})
        return obj_list

    def create_message(self, sender='', to='', subject='', msgHtml='', msgPlain=''):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to
        #msg.attach(MIMEText(msgPlain, 'plain'))
        msg.attach(MIMEText(msgHtml, 'html'))
        raw = base64.urlsafe_b64encode(msg.as_bytes())
        raw = raw.decode()
        body = {'raw': raw}
        return body

    def send_message_internal(self, user_id, message):
        try:
            message = (self._service.users().messages().send(userId=user_id, body=message).execute())
            #print('Message Id: %s' % message['id'])
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def send_message(self, sender, to, subject, msgHtml, msgPlain=''):
        message1 = self.create_message(sender, to, subject, msgHtml, msgPlain)
        return self.send_message_internal("me", message1)

    def get_profile(self):
        results = self._service.users().getProfile(userId='me').execute()
        return results

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'email':
            p = self.get_profile()
            return ({'id': p['emailAddress'], 'name': p['emailAddress']},)
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

    def get_history(self, history_id, f=None):
        params = {'userId': 'me', 'startHistoryId': history_id}
        if f is not None:
            params['historyTypes'] = f
        return self._service.users().history().list(**params).execute()

    def get_message(self, message_id):
        raw_message = self._service.users().messages().get(userId="me", id=message_id, format="raw").execute()
        decoded_message = base64.urlsafe_b64decode(raw_message['raw'].encode('ASCII'))
        text_message = message_from_bytes(decoded_message)
        return text_message

    def get_cleaned_message(self, message='', message_id=''):
        list_content = []
        if message.is_multipart():
            for payload in message.get_payload():
                list_content.append(payload.get_payload())
        else:
            list_content.append(message.get_payload())
        return {'Id': message_id, 'Subject': message['subject'], 'From': message['from'], 'To': message['to'],
                'Date': message['date'], 'Message-Id': message['message-id'], 'Content-Plain': list_content[0],
                'Content-Html': list_content[1]}

    def do_webhook_process(self, body=None, POST=None, **kwargs):
        print("body", body)
        response = HttpResponse(status=200)
        encoded_message_data = base64.urlsafe_b64decode(body['message']['data'].encode('ASCII'))
        decoded_message_data = json.loads(encoded_message_data.decode('utf-8'))
        new_history_id = decoded_message_data['historyId']
        print("new history", new_history_id)
        _email = decoded_message_data['emailAddress']
        print("email", _email)
        plug_list = Plug.objects.filter(Q(gear_source__is_active=True) | Q(is_tested=False),
                                        plug_action_specification__value__iexact=_email,
                                        plug_action_specification__action_specification__name__iexact='email',
                                        action__name='new email')
        print("pluglist", plug_list)
        if plug_list:
            for plug in plug_list:
                try:
                    print(1111)
                    self.create_connection(plug.connection.related_connection, plug)
                    print(22222)
                    history_id = self._connection_object.history
                    print(self._connection_object)
                    ping = self.test_connection()
                    if ping:
                        history = self.get_history(history_id, f='messageAdded')
                        try:
                            message_id = history['history'][0]['messagesAdded'][0]['message']['id']
                        except KeyError:
                            print("error en key en history")
                        message = self.get_message(message_id=message_id)
                        message_dict = self.get_cleaned_message(message, body['message']['messageId'])
                        print("dict")
                        print(message_dict)
                        self._connection_object.history = new_history_id
                        self._connection_object.save(update_fields=['history'])
                        break
                except Exception as e:
                    raise
                    continue
            for plug in plug_list:
                self.create_connection(plug.connection.related_connection, plug)
                if self.test_connection():
                    self.download_source_data(message=message_dict)
                if not self._plug.is_tested:
                    self._plug.is_tested = True
                    self._plug.save(update_fields=['is_tested', ])
        return HttpResponse(status=200)

    @property
    def has_webhook(self):
        return True


class SMTPController(BaseController):
    client = None
    sender_identifier = 'ZAKARA .23'

    def create_connection(self, *args, **kwargs):
        if args:
            super(SMTPController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self.client = SMTPClient(host, port, user, password)
                except Exception as e:
                    print("Error getting the SMS attributes")

    def test_connection(self):
        return self.client is not None and self.client.is_valid_connection()

    def get_target_fields(self, **kwargs):
        return ['recipient', 'message']

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            for obj in data_list:
                r = self.client.send_mail(**obj)
            extra = {'controller': 'smtp'}
            return
        raise ControllerError("Incomplete.")
