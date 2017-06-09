from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import StoredData, PlugSpecification

from slacker import Slacker
from utils.nrsgateway import Client as SMSClient
import json


class SlackController(BaseController):
    _token = None
    _slacker = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(SlackController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._slacker = Slacker(self._token)
                except Exception as e:
                    print("Error getting the Slack Token")
                    print(e)
        elif kwargs:
            print(kwargs)
        return self._token is not None and self._slacker is not None

    def get_channel_list(self):
        response = self._slacker.channels.list()
        if 'successful' in response.__dict__ and response.__dict__['successful'] == True:
            data = json.loads(response.__dict__['raw'])
            channel_list = tuple({'id': c['id'], 'name': c['name']} for c in data['channels'])
            return channel_list

        else:
            return []
            # raise ("Not implemented yet.")

    def post_message_to_target(self, message='', target=''):
        try:
            self._slacker.chat.post_message(target, message)
            return True
        except Exception as e:
            raise
            return False

    def post_message_to_channel(self, message=None, channel=None):
        if message is not None and channel is not None:
            self.post_message_to_target(message=message, target=channel)
        else:
            print("Error: debes enviar message y channel.")
            return False

    def post_message_to_user(self, message=None, user=None):
        if message is not None and user is not None:
            self.post_message_to_target(message=message, target=user)
        else:
            print("Error: debes enviar message y user.")
            return False

    def get_target_fields(self, **kwargs):
        return ['message']

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
            extra = {'controller': 'slack'}
            for specification in self._plug.plug_specification.all():
                try:
                    target = PlugSpecification.objects.get(plug=self._plug,
                                                           action_specification=specification.action_specification)
                except Exception as e:
                    raise
            for obj in data_list:
                l = [val for val in obj.values()]
                obj_list.append(l)
            for o in obj_list:
                res = self.post_message_to_target(o, target.value)
            return
        raise ControllerError("Incomplete.")

    def download_to_stored_data(self, connection_object=None, plug=None, event=None, **kwargs):
        if event is not None:
            new_message = None
            if 'type' in event and event['event']['type'] == 'message':
                print(event['event_id'], event['event_time'], event['event']['text'])
                q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                              object_id=event['event_id'])
                if not q.exists():
                    new_message = StoredData(connection=connection_object.connection, plug=plug,
                                             object_id=event['event_id'], name=event['event']['type'],
                                             value=event['event']['text'])
                extra = {}
                if new_message is not None:
                    extra['status'] = 's'
                    extra = {'controller': 'google_spreadsheets'}
                    self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                        new_message.object_id, new_message.plug.id, new_message.connection.id), extra=extra)
                    new_message.save()
        return False

    def get_mapping_fields(self, **kwargs):
        return self.get_target_fields()


class SMSController(BaseController):
    client = None
    sender_identifier = 'ZAKARA .23'

    def create_connection(self, *args, **kwargs):
        if args:
            super(SMSController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self.client = SMSClient(user, password)
                except Exception as e:
                    print("Error getting the SMS attributes")
                    print(e)
        elif kwargs:
            user = kwargs['connection_user']
            password = kwargs['connection_password']
            self.client = SMSClient(user, password)

        return True

    def get_target_fields(self, **kwargs):
        return ['number_to', 'message']

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
                obj['sender_identifier'] = self.sender_identifier
                print(obj)
                r = self.client.send_message(**obj)
                print(r.status_code)
                print(r.text)
                print(r.url)
            extra = {'controller': 'sms'}
            return
        raise ControllerError("Incomplete.")
