from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField

from mailchimp3 import MailChimp
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
        elif not args and kwargs:
            if 'api_key' in kwargs:
                api_key = kwargs.pop('api_key')
            try:
                self._client = GetResponse(api_key)
                print("%s %s", (api_key))
                print(self._client)
            except Exception as e:
                print(e)
                print("Error getting the GetResponse attributes")
                self._client = None
        t = self.get_campaigns()
        return t is not None

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
            for specification in self._plug.plug_specification.all():
                if specification.action_specification.action.name == 'subscribe':
                    status = 'subscribed'
                elif specification.action_specification.action.name == 'unsubscribe':
                    status = 'unsubscribed'
            extra = {'controller': 'getresponse'}
            for obj in data_list:
                if status == 'subscribed':
                    res = self.subscribe_contact(self._plug.plug_specification.all()[0].value, obj)
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


class MailChimpController(BaseController):
    """
    MailChimpController Class
    """
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MailChimpController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    print(self._connection_object.connection_user, self._connection_object.api_key)
                    self._client = MailChimp(self._connection_object.connection_user, self._connection_object.api_key)
                except Exception as e:
                    print("Error getting the MailChimp attributes")
                    self._client = None
        elif not args and kwargs:
            if 'user' in kwargs:
                user = kwargs.pop('user')
            if 'api_key' in kwargs:
                api_key = kwargs.pop('api_key')
            try:
                self._client = MailChimp(user, api_key)
                print("%s %s", (user, api_key))
                print(self._client)
            except Exception as e:
                print(e)
                print("Error getting the MailChimp attributes")
                self._client = None
        t = self.get_lists()
        return t is not None

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
            for specification in self._plug.plug_specification.all():
                if specification.action_specification.action.name == 'subscribe':
                    status = 'subscribed'
                elif specification.action_specification.action.name == 'unsubscribe':
                    status = 'unsubscribed'
                    _list = self.get_all_members(self._plug.plug_specification.all()[0].value)

            list_id = self._plug.plug_specification.all()[0].value
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
        return self.get_list_merge_fields(**kwargs)

    def get_all_members(self, list_id):
        return self._client.lists.members.all(list_id, get_all=True, fields="members.id,members.email_address")

    def set_members_hash_id(self, members, _list):
        return [dict(m, hash_id=l['id']) for m in members for l in _list['members'] if
                m['email_address'] == l['email_address']]

    def get_mapping_fields(self, **kwargs):
        list_id = self._plug.plug_specification.all()[0].value
        mfl = [MapField(f, controller=ConnectorEnum.MailChimp) for f in self.get_list_merge_fields(list_id)]
        mfl.append(MapField({'tag': 'email_address', 'name': 'Email', 'required': True, 'type': 'email',
                             'options': {'size': 100}}, controller=ConnectorEnum.MailChimp))
        return mfl
