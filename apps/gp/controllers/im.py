from django.http import JsonResponse, HttpResponse
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import StoredData, PlugActionSpecification, \
    ActionSpecification
from apps.gp.map import MapField
from apps.gp.enum import ConnectorEnum
from slacker import Slacker
from utils.nrsgateway import Client as SMSClient
import json


class SlackController(BaseController):
    _token = None
    _slacker = None

    def __init__(self, connection=None, plug=None, **kwargs):
        BaseController.__init__(self, connection=connection, plug=plug,
                                **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(SlackController, self).create_connection(
            connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
                self._slacker = Slacker(self._token)
            except Exception as e:
                print("Error getting the Slack Token")

    def test_connection(self):
        if self._token is not None and self._slacker is not None:
            response = self.get_channel_list()
            if isinstance(response, tuple):
                return True
        return False

    def get_channel_list(self):
        response = self._slacker.channels.list()
        _dict = response.__dict__
        if 'successful' in _dict and _dict['successful'] is True:
            data = json.loads(_dict['raw'])
            channel_list = tuple(
                {'id': c['id'], 'name': c['name']} for c in data['channels'])
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
        return [{'name': 'message'}]

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
            for specification in self._plug.plug_action_specification.all():
                try:
                    target = PlugActionSpecification.objects.get(
                        plug=self._plug,
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

    def download_to_stored_data(self, connection_object=None, plug=None,
                                event=None, **kwargs):
        if event is not None:
            new_message = None
            if 'type' in event and event['event']['type'] == 'message':
                q = StoredData.objects.filter(
                    connection=connection_object.connection, plug=plug,
                    object_id=event['event_id'])
                if not q.exists():
                    new_message = StoredData(
                        connection=connection_object.connection, plug=plug,
                        object_id=event['event_id'],
                        name=event['event']['type'],
                        value=event['event']['text'])
                extra = {}
                if new_message is not None:
                    extra['status'] = 's'
                    extra = {'controller': 'slack'}
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            new_message.object_id, new_message.plug.id,
                            new_message.connection.id), extra=extra)
                    new_message.save()
            return new_message is not None
        return False

    def get_mapping_fields(self, **kwargs):
        return [MapField(f, controller=ConnectorEnum.Slack) for f in
                self.get_target_fields()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'channel':
            return tuple({'id': c['id'], 'name': c['name']} for c in
                         self.get_channel_list())
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

    def do_webhook_process(self, body=None, POST=None, **kwargs):
        """
            Devuelve un response
        """
        if 'challenge' in body.keys():
            return JsonResponse({'challenge': body['challenge']})
        elif 'type' in body.keys() and body['type'] == 'event_callback':
            response = HttpResponse(status=200)
            event = body['event']
            if event['type'] == "message":
                regular_query = {
                    'action_specification__action__action_type': 'source',
                    'action_specification__action__connector__name__iexact': 'slack',
                    'plug__gear_source__is_active': True,
                    'value': event['channel'], }
                testing_plugs_query = {
                    'action_specification__action__action_type': 'source',
                    'action_specification__action__connector__name__iexact': 'slack',
                    'plug__gear_source__is_active': False,
                    'plug__is_tested': False,
                    'value': event['channel'], }
                channel_list = PlugActionSpecification.objects.filter(
                    **regular_query)
                test_channel_list = PlugActionSpecification.objects.filter(
                    **testing_plugs_query)
                for channel in channel_list:
                    self._connection_object, self._plug = channel.plug.connection.related_connection, channel.plug
                    self.download_source_data(event=body)
                for channel in test_channel_list:
                    self._connection_object, self._plug = channel.plug.connection.related_connection, channel.plug
                    self.download_source_data(event=body)
                    self._plug.is_tested = True
                    self._plug.save(update_fields=['is_tested', ])
        else:
            print("No callback event")
        return response


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

    def test_connection(self):
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

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return fields
