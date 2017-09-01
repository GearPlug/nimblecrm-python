import datetime
import mandrill
from django.core.urlresolvers import reverse
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.models import ActionSpecification, Webhook, StoredData

from mailchimp.client import Client
from getresponse.client import GetResponse


class GetResponseController(BaseController):
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(GetResponseController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._client = GetResponse(self._connection_object.api_key)
                except Exception as e:
                    print("Error getting the GetResponse attributes")
                    self._client = None

    def test_connection(self):
        return self._client is not None and self.get_campaigns() is not None

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
            status = None
            for specification in self._plug.plug_action_specification.all():
                if specification.action_specification.action.name == 'subscribe':
                    status = 'subscribed'
                elif specification.action_specification.action.name == 'unsubscribe':
                    status = 'unsubscribed'
            extra = {'controller': 'getresponse'}
            for obj in data_list:
                if status == 'subscribed':
                    res = self.subscribe_contact(self._plug.plug_action_specification.all()[0].value, obj)
                else:
                    res = self.unsubscribe_contact(obj)
            return
        raise ControllerError("Incomplete.")

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
            _dict["customFieldValues"] = [{"customFieldId": k, "value": [v]} for k, v in obj.items()]
        self._client.create_contact(_dict)

    def unsubscribe_contact(self, obj):
        self._client.delete_contact(obj.pop('id'))

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
                'id': field.id,
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
            'name': 'id',
            'required': True,
            'type': 'text',

        }]

    def get_mapping_fields(self, **kwargs):
        if self._plug.plug_action_specification.all()[0].action_specification.action.name == 'Unsubscribe':
            fields = self.get_unsubscribe_target_fields()
        else:
            fields = self.get_meta()
        return [MapField(f, controller=ConnectorEnum.GetResponse) for f in fields]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'campaign':
            return tuple({'id': c['id'], 'name': c['name']} for c in self.get_campaigns())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


class MailChimpController(BaseController):
    """
    MailChimpController Class
    """
    _client = None
    _token= None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MailChimpController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token=self._connection_object.token
                    self._client = Client(access_token=self._token)
                except Exception as e:
                    print("Error getting the MailChimp attributes")
                    self._client = None
                    self._token= None

    def test_connection(self):
            try:
                self._client.get_lists()
                return self._client is not None and self._token is not None
            except Exception as e:
                print(e)
                return self._client is None and self._token is None

    def get_lists(self):
        if self._client:
            result = self._client.lists.all()
            try:
                return [{'name': l['name'], 'id': l['id']} for l in result['lists']]
            except:
                return []
        return []

    def get_list_merge_fields(self, list_id):
        result = self._client.lists._mc_client._get(url='lists/%s/merge-fields' % list_id)
        try:
            return result['merge_fields']
        except:
            return []

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
                except:
                    data_list = []
        if self._plug is not None:
            status = None
            _list = None
            for specification in self._plug.plug_action_specification.all():
                if specification.action_specification.action.name == 'subscribe':
                    status = 'subscribed'
                elif specification.action_specification.action.name == 'unsubscribe':
                    status = 'unsubscribed'
                    _list = self.get_all_members(self._plug.plug_action_specification.all()[0].value)

            list_id = self._plug.plug_action_specification.all()[0].value
            for obj in data_list:
                d = {'email_address': obj.pop('email_address'), 'status': status,
                     'merge_fields': {key: obj[key] for key in obj.keys()}}
                obj_list.append(d)

            if status == 'unsubscribed':
                obj_list = self.set_members_hash_id(obj_list, _list)

            extra = {'controller': 'mailchimp'}
            for item in obj_list:
                try:
                    if status == 'subscribed':
                        res = self._client.lists.members.create(list_id, item)
                    elif status == 'unsubscribed':
                        res = self._client.lists.members.update(list_id, item['hash_id'], {'status': 'unsubscribed'})
                    extra['status'] = "s"
                    self._log.info('Email: %s  successfully sent. Result: %s.' % (item['email_address'], res['id']),
                                   extra=extra)
                except Exception as e:
                    print(e)
                    res = "User already exists"
                    extra['status'] = 'f'
                    self._log.error('Email: %s  failed. Result: %s.' % (item['email_address'], res), extra=extra)
            return
        raise ControllerError("Incomplete.")

    def get_target_fields(self, **kwargs):
        return {}

    def get_all_members(self, list_id):
        return self._client.lists.members.all(list_id, get_all=True, fields="members.id,members.email_address")

    def set_members_hash_id(self, members, _list):
        return [dict(m, hash_id=l['id']) for m in members for l in _list['members'] if
                m['email_address'] == l['email_address']]

    def get_mapping_fields(self, **kwargs):
        list = self._plug.plug_action_specification.get(action_specification__name__iexact='list')
        list_id = list.value
        print("LIST ID->>", list_id)
        mfl = [MapField(f, controller=ConnectorEnum.MailChimp) for f in self.get_list_merge_fields(list_id)]
        mfl.append(MapField({'tag': 'email_address', 'name': 'Email', 'required': True, 'type': 'email',
                             'options': {'size': 100}}, controller=ConnectorEnum.MailChimp))
        return mfl

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'list':
            return tuple({'id': c['id'], 'name': c['name']} for c in self._client.get_lists()['lists'])
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


class MandrillController(BaseController):
    """
    MandrillController Class
    """
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MandrillController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._client = mandrill.Mandrill(self._connection_object.api_key)
                except Exception as e:
                    print("Error getting the Mandrill attributes")
                    self._client = None

    def test_connection(self):
        try:
            return self._client is not None and self._client.users.info() is not None
        except mandrill.InvalidKeyError:
            return False

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
            extra = {'controller': 'mandrill'}
            for obj in data_list:
                res = self.send_email(obj)
            return
        raise ControllerError("Incomplete.")

    def send_email(self, obj):
        to_email = obj.pop('to_email')
        obj['to'] = [{'email': to_email}]
        print(obj)
        result = self._client.messages.send(message=obj, async=False, ip_pool='Main Pool',
                                            send_at=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        print(result)

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
                'required': False,
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
        mfl = [MapField(f, controller=ConnectorEnum.Mandrill) for f in self.get_meta()]
        return mfl

    def get_target_fields(self):
        return self.get_meta()

    def get_events(self):
        return ['send', 'hard_bounce', 'soft_bounce', 'open', 'click', 'spam', 'unsub', 'reject']

    def download_to_stored_data(self, connection_object=None, plug=None, event=None, **kwargs):
        if event is not None:
            _items = []
            # Todo verificar que este ID siempre existe independiente del action

            event_id = event.pop('_id')
            msg = event.pop('msg')
            event.update(msg)
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=event_id)
            if not q.exists():
                for k, v in event.items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=event_id, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'mandril'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'event':
            return tuple({'id': e, 'name': e} for e in self.get_events())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def create_webhook(self):
        action = self._plug.action.name
        if action == 'new email':
            event = self._plug.plug_action_specification.get(action_specification__name='event')

            # Creacion de Webhook
            webhook = Webhook.objects.create(name='mandrill', plug=self._plug, url='', expiration='')

            # Verificar ngrok para determinar url_base
            url_base = 'https://fbaa4455.ngrok.io'
            url_path = reverse('home:webhook', kwargs={'connector': 'mandrill', 'webhook_id': webhook.id})
            url = url_base + url_path

            try:
                events = [event.value]
                response = self._client.webhooks.add(url=url, description='GearPlug Webhook', events=events)
                # El cliente parsea el response por lo cual siempre viene un diccionario.
                webhook.url = url
                webhook.generated_id = response['id']
                webhook.is_active = True
                webhook.save(update_fields=['url', 'generated_id', 'is_active'])
                return True
            except mandrill.Error as e:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
                return False
