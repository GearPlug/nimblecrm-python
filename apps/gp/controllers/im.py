from django.http import JsonResponse, HttpResponse
from django.db.models import Q
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.models import StoredData, ActionSpecification, Plug
from apps.gp.map import MapField
from apps.gp.enum import ConnectorEnum
from slacker import Slacker
from utils.nrsgateway import Client as SMSClient
import json
import re


class SlackController(BaseController):
    _token = None
    _slacker = None

    def __init__(self, connection=None, plug=None, **kwargs):
        BaseController.__init__(self, connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(SlackController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
            except Exception as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.Slack.name,
                                      message='The attributes necessary to make the connection were not obtained. {}'.format(
                                          str(e)))
            try:
                self._slacker = Slacker(self._token)
            except Exception as e:
                raise ControllerError(code=1003, controller=ConnectorEnum.Slack.name,
                                      message='Error in the instantiation of the client. {}'.format(str(e)))

    def test_connection(self):
        try:
            response = self._slacker.api.test()
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.Slack.name,
            #                       message='Error in the connection test. {}'.format(str(e)))
            return False

        body = response.body
        if 'ok' in body and body['ok'] is True:
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

    def post_message_to_target(self, message='', target=''):
        try:
            return self._slacker.chat.post_message(target, message)
        except Exception as e:
            # raise
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

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        result_list = []
        response = {}
        target = self._plug.plug_action_specification.get(action_specification__name='channel')
        for obj in data_list:
            l = [val for val in obj.values()]
            obj_list.append(l)
        for o in obj_list:
            response['data'] = {'message': o[0]}
            sent = False
            try:
                result = self.post_message_to_target(o, target.value)
                sent = True
                _dict = result.__dict__
                response['response'] = str(_dict['body']['message'])
                response['sent'] = sent
                response['identifier'] = _dict['body']['ts']
            except Exception as e:
                # raise
                print(e)
                response['response'] = "error al enviar el mensaje"
                response['sent'] = sent
                response['identifier'] = ""
            result_list.append(response)
        return result_list

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
                is_stored = False
                if new_message is not None:
                    extra['status'] = 's'
                    extra = {'controller': 'slack'}
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            new_message.object_id, new_message.plug.id,
                            new_message.connection.id), extra=extra)
                    new_message.save()
                    is_stored = True
                    result_list = [{'raw': {new_message.name: new_message.value}, 'is_stored': is_stored,
                                    'identifier': {'name': 'event_id', 'value': new_message.object_id}}]
                    return {'downloaded_data': result_list, 'last_source_record': new_message.object_id}
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
                # channel_list = PlugActionSpecification.objects.filter(
                #     Q(plug__gear_source__is_active=True) | Q(plug__is_tested=False),
                #     plug_action_specification__action__action_type='source',
                #     action_specification__action__connector__name__iexact='slack',
                #     value=event['channel'],
                # )
                channel_list = Plug.objects.filter(
                    Q(gear_source__is_active=True) | Q(is_tested=False),
                    plug_action_specification__value__iexact=event['channel'],
                    plug_action_specification__action_specification__name__iexact='channel',
                    action__name='new message posted to a chanel', )
                for channel in channel_list:
                    self.create_connection(channel.connection.related_connection, channel)
                    self.download_source_data(event=body)
                    if not self._plug.is_tested:
                        self._plug.is_tested = True
                        self._plug.save(update_fields=['is_tested', ])
        else:
            print("No callback event")
        return response


class SMSController(BaseController):
    client = None
    sender_identifier = 'ZAKARA .23'
    is_active = False

    def __init__(self, connection=None, plug=None, **kwargs):
        super(SMSController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(SMSController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
                self.client = SMSClient(user, password)
                self.is_active = True
            except Exception as e:
                print(e)
                self.is_active = False

    def test_connection(self):
        return self.is_active

    def get_target_fields(self, **kwargs):
        return [{'name': 'number_to', 'label': 'to', 'type': 'varchar', 'required': True},
                {'name': 'message', 'label': 'text', 'type': 'varchar', 'required': True}, ]

    def get_mapping_fields(self, **kwargs):
        return [MapField(f, controller=ConnectorEnum.SMS) for f in self.get_target_fields()]

    def send_stored_data(self, data_list):
        obj_list = []
        regex = re.compile('ID (\\d+)')
        for obj in data_list:
            obj['sender_identifier'] = self.sender_identifier
            try:
                r = self.client.send_message(**obj)
                r = r.text
                sent = True
                try:
                    identifier = regex.findall(r)[0]
                except IndexError:
                    identifier = "-1"
            except:
                r = 'Could not send the message. Please check the data was valid and try again.'
                sent = False
                identifier = '-1'
            obj_list.append({'data': obj, 'response': r, 'identifier': identifier, 'sent': sent})
        return obj_list
