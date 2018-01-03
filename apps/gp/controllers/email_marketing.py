import datetime
import mandrill
from django.core.urlresolvers import reverse
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.models import ActionSpecification, Webhook, StoredData, Action
from django.conf import settings
from mailchimp.client import Client
from getresponse.client import GetResponse


class GetResponseController(BaseController):
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        BaseController.__init__(self, connection=connection, plug=plug,
                                **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(GetResponseController, self).create_connection(
            connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._client = GetResponse(self._connection_object.api_key)
            except Exception as e:
                print("Error getting the GetResponse attributes")
                self._client = None

    def test_connection(self):
        try:
            self.get_campaigns()
            return self._client is not None
        except:
            return self._client is None

    def send_stored_data(self, data_list):
        obj_list = []
        _action = self._plug.action.name
        for obj in data_list:
            if _action == 'subscribe':
                try:
                    res = self.subscribe_contact(self._plug.plug_action_specification.all()[0].value, obj)
                    if res is True:
                        _sent = True
                    else:
                        _sent = False
                except:
                    _sent = False
                    res = ""
            elif _action == 'Unsubscribe':
                try:
                    _campaign = self._plug.plug_action_specification.get(action_specification__name='campaign')
                    res = self.unsubscribe_contact(obj, _campaign.value)
                    if res is True:
                        _sent = True
                    else:
                        _sent = False
                except:
                    _sent = False
                    res = ""
            else:
                print("action not found")
            obj_list.append({'data':dict(obj), 'response': res, 'sent':_sent, 'identifier':''})
        return obj_list


    def subscribe_contact(self, campaign_id, obj):
        _dict = {
            "email": obj.pop('email'),
            "campaign": {"campaignId": campaign_id}
        }
        if 'name' in obj:
            _dict['name'] = obj.pop('name')
        if 'dayOfCycle' in obj:
            _dict['dayOfCycle'] = obj.pop('dayOfCycle')
        if 'ipAddress' in obj:
            _dict['ipAddress'] = obj.pop('ipAddress')
        if obj:
            _dict["customFieldValues"] = [{"customFieldId": k, "value": [v]}
                                          for k, v in obj.items()]
        return self._client.create_contact(_dict)

    def unsubscribe_contact(self, obj, _campaign_id):
        _email = obj.pop('email')
        print("email", _email)
        _contacts = self._client.get_campaign_contacts(_campaign_id)
        print("contacts", _contacts)
        _id = None
        for contact in _contacts:
            if contact.email == _email:
                _id = contact.id
        if _id is not None:
            return self._client.delete_contact(_id)
        else:
            raise ControllerError("Email have not been found")


    def get_campaigns(self):
        if self._client:
            result = self._client.get_campaigns({'sort': {'name', 'desc'}})
            try:
                return [{'name': l.name, 'id': l.id} for l in result]
            except:
                return []
        return []

    def get_meta(self):
        _list = [{
            'name': 'name',
            'required': False,
            'type': 'text',

        }, {
            'name': 'email',
            'required': True,
            'type': 'text',

        }, {
            'name': 'dayOfCycle',
            'required': False,
            'type': 'text',

        }, {
            'name': 'ipAddress',
            'required': False,
            'type': 'text',

        }]
        fields = self._client.get_custom_fields({'sort': {'name', 'desc'}})
        for field in fields:
            _list.append({
                'name': field.name,
                'required': False,
                'type': field.field_type,
                'values': field.values,
            })
        return _list

    def get_target_fields(self):
        return self.get_meta()

    def get_unsubscribe_target_fields(self):
        return [{
            'name': 'email',
            'required': True,
            'type': 'text',

        }]

    def get_mapping_fields(self, **kwargs):
        if self._plug.plug_action_specification.all()[
            0].action_specification.action.name == 'Unsubscribe':
            fields = self.get_unsubscribe_target_fields()
        else:
            fields = self.get_meta()
        return [MapField(f, controller=ConnectorEnum.GetResponse) for f in
                fields]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'campaign':
            return tuple({'id': c['id'], 'name': c['name']} for c in
                         self.get_campaigns())
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")


class MailChimpController(BaseController):
    """
    MailChimpController Class
    """
    _client = None
    _token = None

    def __init__(self, connection=None, plug=None, **kwargs):
        BaseController.__init__(self, connection=connection, plug=plug,
                                **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(MailChimpController, self).create_connection(
            connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
                self._client = Client(access_token=self._token)
            except Exception as e:
                print("Error getting the MailChimp attributes")
                self._client = None
                self._token = None

    def test_connection(self):
        try:
            self._client.get_lists()
            return True
        except Exception as e:
            print(e)
            return False

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        action = Action.objects.get(plug__plug_action_specification=self._plug.plug_action_specification.first())
        list_id = self._plug.plug_action_specification.filter(action_specification__action=action).first().value
        try:
            status = action.name + "d"
        except:
            status = None
        list_id = self._plug.plug_action_specification.filter(action_specification__action=action).first().value
        _list = [{'email_address': obj.pop('email_address'), 'status': status,
                  'merge_fields': {key: obj[key] for key in obj.keys()}} for obj in data_list]
        for item in _list:
            obj_result = {'data': dict(item)}
            try:
                res = self._client.add_new_list_member(list_id, item)
                obj_result['response'] = res
                obj_result['sent'] = True
                obj_result['identifier'] = res['id']
            except Exception as e:
                obj_result['response'] = str(e)
                obj_result['sent'] = False
                obj_result['identifier'] = '-1'
            obj_list.append(obj_result)
        return obj_list

    def get_target_fields(self, **kwargs):
        return [{"name": "email_address", "required": True, "type": "varchar",
                 "label": "email"},
                {"name": "FNAME", "required": False, "type": "varchar",
                 "label": "First Name"},
                {"name": "LNAME", "required": False, "type": "varchar",
                 "label": "Last Name"},
                ]

    def get_mapping_fields(self, **kwargs):
        return [MapField(f, controller=ConnectorEnum.MailChimp) for f in
                self.get_target_fields()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'list':
            return tuple({'id': c['id'], 'name': c['name']} for c in
                         self._client.get_lists()['lists'])
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")


class MandrillController(BaseController):
    """
    MandrillController Class
    """
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(MandrillController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(MandrillController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                api_key = self._connection_object.api_key
            except Exception as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.Mandrill,
                                      message='The attributes necessary to make the connection were not obtained. {}'.format(str(e)))
        else:
            raise ControllerError(code=1002, controller=ConnectorEnum.Mandrill,
                                  message='The controller is not instantiated correctly.')
        try:
            self._client = mandrill.Mandrill(api_key)
        except Exception as e:
            raise ControllerError(code=1003, controller=ConnectorEnum.Mandrill,
                                  message='Error in the instantiation of the client. {}'.format(
                                      str(e)))

    def test_connection(self):
        try:
            user_info = self._client.users.info()
        except mandrill.InvalidKeyError:
            # raise ControllerError(code=1004, controller=ConnectorEnum.Mandrill,
            #                       message='Error InvalidKeyError. {}'.format(
            #                           str(e)))
            return False
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.Mandrill,
            #                       message='Error in the connection test.. {}'.format(
            #                           str(e)))
            return False
        if user_info is not None:
            return True
        else:
            return False

    def send_stored_data(self, data_list):
        """
        Se debe configurar en la cuenta Domain, DKIM Settings, SPF Settings, para que los emails sean entregados. El proceso funciona pero los emails son colocados en cola
        """
        obj_list = []
        for obj in data_list:
            _response = self.send_email(obj)
            if '_id' in _response[0]:
                _sent = True
                _identifier = _response[0]['_id']
            else:
                _sent = False
                _identifier = ""
            obj_list.append({'data': dict(obj), 'response': _response, 'sent': _sent, 'identifier': _identifier})
        return obj_list

    def send_email(self, obj):
        to_email = obj.pop('to_email')
        obj['to'] = [{'email': to_email}]
        result = self._client.messages.send(message=obj, async=False,
                                            ip_pool='Main Pool',
                                            send_at=datetime.datetime.now().strftime(
                                                '%Y-%m-%d %H:%M:%S'))
        return result

    def get_meta(self):
        _dict = [
            # {
            #     'name': 'attachments',
            #     'required': False,
            #     'type': 'file'
            # },
            {
                'name': 'auto_html',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'auto_text',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'bcc_address',
                'required': False,
                'type': 'text'
            }, {
                'name': 'from_email',
                'required': False,
                'type': 'text'
            }, {
                'name': 'from_name',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'global_merge_vars',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'google_analytics_campaign',
                'required': False,
                'type': 'text'
            },
            {
                'name': 'google_analytics_domains',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'headers',
            #     'required': False,
            #     'type': 'struct'
            # },
            {
                'name': 'html',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'images',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'important',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'inline_css',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'merge',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'merge_language',
                'required': False,
                'type': 'text'
            },
            # {
            #     'name': 'merge_vars',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'metadata',
                'required': False,
                'type': 'array'
            }, {
                'name': 'preserve_recipients',
                'required': False,
                'type': 'bool'
            },
            # {
            #     'name': 'recipient_metadata',
            #     'required': False,
            #     'type': 'array'
            # },
            {
                'name': 'return_path_domain',
                'required': False,
                'type': 'text'
            }, {
                'name': 'signing_domain',
                'required': False,
                'type': 'text'
            }, {
                'name': 'subaccount',
                'required': False,
                'type': 'text'
            }, {
                'name': 'subject',
                'required': False,
                'type': 'text'
            }, {
                'name': 'tags',
                'required': False,
                'type': 'array'
            }, {
                'name': 'text',
                'required': False,
                'type': 'text'
            },
            # To: originalmente una lista de diccionarios
            {
                'name': 'to_email',
                'required': True,
                'type': 'text'
            },
            {
                'name': 'track_clicks',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'track_opens',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'tracking_domain',
                'required': False,
                'type': 'text'
            }, {
                'name': 'url_strip_qs',
                'required': False,
                'type': 'bool'
            }, {
                'name': 'view_content_link',
                'required': False,
                'type': 'bool'
            },
        ]
        return _dict

    def get_mapping_fields(self, **kwargs):
        mfl = [MapField(f, controller=ConnectorEnum.Mandrill) for f in
               self.get_meta()]
        return mfl

    def get_target_fields(self):
        return self.get_meta()

    # Los specifications existen para source y por el momento solo se tiene una acción de target

    # def get_events(self):
    #     return ['send', 'hard_bounce', 'soft_bounce', 'open', 'click', 'spam',
    #             'unsub', 'reject']

    # Por ahora solo funciona como target

    # def download_to_stored_data(self, connection_object=None, plug=None,
    #                             event=None, **kwargs):
    #     if event is not None:
    #         _items = []
    #         # Todo verificar que este ID siempre existe independiente del action
    #
    #         event_id = event.pop('_id')
    #         msg = event.pop('msg')
    #         event.update(msg)
    #         q = StoredData.objects.filter(
    #             connection=connection_object.connection, plug=plug,
    #             object_id=event_id)
    #         if not q.exists():
    #             for k, v in event.items():
    #                 obj = StoredData(connection=connection_object.connection,
    #                                  plug=plug,
    #                                  object_id=event_id, name=k, value=v or '')
    #                 _items.append(obj)
    #         extra = {}
    #         for item in _items:
    #             extra['status'] = 's'
    #             extra = {'controller': 'mandril'}
    #             self._log.info(
    #                 'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
    #                     item.object_id, item.plug.id, item.connection.id),
    #                 extra=extra)
    #             item.save()
    #     return False

    # Los specifications existen para source y por el momento solo se tiene una acción de target

    # def get_action_specification_options(self, action_specification_id):
    #     action_specification = ActionSpecification.objects.get(
    #         pk=action_specification_id)
    #     if action_specification.name.lower() == 'event':
    #         return tuple({'id': e, 'name': e} for e in self.get_events())
    #     else:
    #         raise ControllerError(
    #             "That specification doesn't belong to an action in this connector.")

    # Por ahora solo funciona como target

    # def create_webhook(self):
    #     action = self._plug.action.name
    #     if action == 'new email':
    #         event = self._plug.plug_action_specification.get(
    #             action_specification__name='event')
    #
    #         # Creacion de Webhook
    #         webhook = Webhook.objects.create(name='mandrill', plug=self._plug,
    #                                          url='', expiration='')
    #
    #         # Verificar ngrok para determinar url_base
    #         url_base = settings.WEBHOOK_HOST
    #         url_path = reverse('home:webhook', kwargs={'connector': 'mandrill',
    #                                                    'webhook_id': webhook.id})
    #         url = url_base + url_path
    #
    #         try:
    #             events = [event.value]
    #             response = self._client.webhooks.add(url=url,
    #                                                  description='GearPlug Webhook',
    #                                                  events=events)
    #             # El cliente parsea el response por lo cual siempre viene un diccionario.
    #             webhook.url = url
    #             webhook.generated_id = response['id']
    #             webhook.is_active = True
    #             webhook.save(
    #                 update_fields=['url', 'generated_id', 'is_active'])
    #             return True
    #         except mandrill.Error as e:
    #             webhook.is_deleted = True
    #             webhook.save(update_fields=['is_deleted', ])
    #             return False

    @property
    def has_webhook(self):
        return True
