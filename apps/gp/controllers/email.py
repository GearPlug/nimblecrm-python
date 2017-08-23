from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.map import MapField
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Webhook, StoredData, ActionSpecification
from utils.smtp_sender import smtpSender as SMTPClient
from oauth2client import client as GoogleClient
from apiclient import discovery, errors
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import httplib2
import base64



class GmailController(BaseController):
    _credential = None

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

    def test_connection(self):
        try:
            self._refresh_token()
            http_auth = self._credential.authorize(httplib2.Http())
            service = discovery.build('gmail', 'v1', http=http_auth)
        except Exception as e:
            print("Error Test connection Gmail")
            service = None
        return service is not None

    def _refresh_token(self, token=''):
        if self._credential.access_token_expired:
            self._credential.refresh(httplib2.Http())
            self._upate_connection_object_credentials()

    def _upate_connection_object_credentials(self):
        self._connection_object.credentials_json = self._credential.to_json()
        self._connection_object.save()

    def create_webhook(self):
        action = self._plug.action.name
        if action == 'Read message':
            # Creacion de Webhook
            webhook = Webhook.objects.create(name='gmail', plug=self._plug, url='')
            credentials = self._credential
            http = credentials.authorize(httplib2.Http())
            service = discovery.build('gmail', 'v1', http=http)
            request = {
                'labelIds': ['INBOX'],
                'topicName': 'projects/gearplug-167220/topics/gearplug',
                'name': 'webhook'
            }
            res_watch = service.users().watch(userId='me', body=request).execute()
            if res_watch['historyId'] is not None:
                webhook.url = 'https://g.grplug.com/webhook/gmail/0/'
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
            id=message['messageId']
            q = StoredData.objects.filter(
                connection=connection_object.connection, plug=plug,
                object_id=id)
            task_stored_data = []

            extra = {}
            for task in task_stored_data:
                try:
                    extra['status'] = 's'
                    extra = {'controller': 'gmail'}
                    task.save()
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            task.object_id, task.plug.id,
                            task.connection.id),
                        extra=extra)
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s failed.' % (
                            task.object_id, task.plug.id,
                            task.connection.id),
                        extra=extra)
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

    def send_message_internal(self, service, user_id, message):
        try:
            message = (service.users().messages().send(userId=user_id, body=message).execute())
            print('Message Id: %s' % message['id'])
            return message
        except errors.HttpError as error:
            print('An error occurred: %s' % error)

    def send_message(self, sender, to, subject, msgHtml, msgPlain):
        credentials = self._credential
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('gmail', 'v1', http=http)
        message1 = self.create_message(sender, to, subject, msgHtml, msgPlain)
        return self.send_message_internal(service, "me", message1)

    def get_profile(self):
        credentials = self._credential
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('gmail', 'v1', http=http)
        results = service.users().getProfile(userId='me').execute()
        return results

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'email':
            p = self.get_profile()
            return ({'id': p['emailAddress'], 'name': p['emailAddress']}, )
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

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
