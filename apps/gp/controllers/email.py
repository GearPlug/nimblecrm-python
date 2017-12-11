from apps.gp.controllers.base import BaseController
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


class GmailController(BaseController):
    _credential = None
    _service = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        credentials_json = None
        if args:
            super(GmailController, self).create_connection(*args)
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
            self._refresh_token()
        except GoogleClient.HttpAccessTokenRefreshError:
            print("ERROR EL TOKEN NO TIENE REFRESH TOKEN")
            return False
        except Exception as e:
            raise
            print("Error Test connection Gmail")
            self._service = None
        return self._service is not None

    def _refresh_token(self, token=''):
        if self._credential.access_token_expired:
            self._credential.refresh(httplib2.Http())
            self._upate_connection_object_credentials()
            self._service = discovery.build('gmail', 'v1', http=self._credential.authorize(httplib2.Http()))

    def _upate_connection_object_credentials(self):
        self._connection_object.credentials_json = self._credential.to_json()
        self._connection_object.save()

    def create_webhook(self):
        action = self._plug.action.name
        if action.lower() == 'new email':
            # Creacion de Webhook
            webhook = Webhook.objects.create(name='gmail', plug=self._plug, url='')
            request = {
                'labelIds': ['INBOX'],
                'topicName': 'projects/gearplug-167220/topics/gearplug',
                'name': 'webhook'
            }
            res_watch = self._service.users().watch(userId='me', body=request).execute()
            if res_watch['historyId'] is not None:
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
        if message is not None:
            id = message['Id']
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id)
            if not q.exists():
                message_stored_data = []
                for k, v in message.items():
                    message_stored_data.append(
                        StoredData(connection=connection_object.connection, plug=plug, name=k, value=v, object_id=id))
            extra = {}
            for msg in message_stored_data:
                try:
                    extra['status'] = 's'
                    extra = {'controller': 'gmail'}
                    msg.save()
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (msg.object_id, msg.plug.id,
                                                                                        msg.connection.id), extra=extra)
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s failed.' % (msg.object_id, msg.plug.id,
                                                                           msg.connection.id), extra=extra)
            return True
        return False

    def get_target_fields(self, **kwargs):
        return [{'name': 'to', 'type': 'varchar', 'required': True},
                {'name': 'sender', 'type': 'varchar', 'required': True},
                {'name': 'subject', 'type': 'varchar', 'required': True},
                {'name': 'msgHtml', 'type': 'varchar', 'required': True},
                {'name': 'msgPlain', 'type': 'varchar', 'required': True}]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Gmail) for f in fields]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'gmail'}
            for item in data_list:
                email = self.send_message(**item)
                if email['id']:
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (email['id']), extra=extra)
                    obj_list.append(email['id'])
                else:
                    extra['status'] = 'f'
                    self._log.info('Item: failed to send.', extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def create_message(self, sender='', to='', subject='', msgHtml='', msgPlain=''):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = sender
        msg['To'] = to
        msg.attach(MIMEText(msgPlain, 'plain'))
        msg.attach(MIMEText(msgHtml, 'html'))
        raw = base64.urlsafe_b64encode(msg.as_bytes())
        raw = raw.decode()
        body = {'raw': raw}
        return body

    def send_message_internal(self, user_id, message):
        try:
            message = (self._service.users().messages().send(userId=user_id, body=message).execute())
            print('Message Id: %s' % message['id'])
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def send_message(self, sender, to, subject, msgHtml, msgPlain):
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

    def get_history(self, history_id):
        return self._service.users().history().list(userId="me", startHistoryId=history_id).execute()

    def get_message(self, message_id):
        raw_message = self._service.users().messages().get(userId='me', id=message_id, format='raw').execute()
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
        response = HttpResponse(status=400)

        encoded_message_data = base64.urlsafe_b64decode(body['message']['data'].encode('ASCII'))
        decoded_message_data = json.loads(encoded_message_data.decode('utf-8'))
        history_id = decoded_message_data['historyId']
        email = decoded_message_data['emailAddress']
        plug_list = Plug.objects.filter(Q(gear_source__is_active=True) | Q(is_tested=False),
                                        plug_type__iexact="source", action__name__iexact="read message",
                                        plug_action_specification__value__iexact=email)
        if plug_list:
            for plug in plug_list:
                try:
                    self.create_connection(plug.connection.related_connection, plug)
                    if self.test_connection():
                        history = self.get_history(history_id)
                        message_id = history['history'][0]['messages'][0]['id']
                        message = self.get_message(message_id=message_id)
                        message_dict = self.get_cleaned_message(message, message_id)
                        break
                except Exception as e:
                    continue
            for plug in plug_list:
                try:
                    self.create_connection(plug.connection.related_connection, plug)
                    if self.test_connection():
                        self.download_source_data(message=message_dict)
                except:
                    pass
            response.status_code = 200
        return response

    @property
    def has_webhook(self):
        return True


class SMTPController(BaseController):
    client = None
    sender_identifier = 'ZAKARA .23'  # TODO: get from settings

    def __init__(self, connection=None, plug=None, **kwargs):
        super(SMTPController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(SMTPController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                host = self._connection_object.host
                port = self._connection_object.port
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
                self.client = SMTPClient(host, port, user, password)
            except Exception as e:
                print("Error getting the SMTP attributes")

    def test_connection(self):
        print("hola")
        print(self.client)
        return self.client is not None and self.client.is_valid_connection()

    def get_target_fields(self, **kwargs):
        print("fields")
        return ['recipient', 'message']

    def send_stored_data(self, data_list):
        obj_list = []

        # data, response, sent, identifier
        for obj in data_list:
            print("1----------------")
            print(obj)
            r = self.client.send_mail(**obj)
            print(r)
            obj_list.append({'data': obj, 'response': r, 'identifier': '-1', 'sent': True})
        return obj_list
