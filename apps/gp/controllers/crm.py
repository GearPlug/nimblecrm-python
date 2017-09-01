import json
import os
import string
import urllib.error
import urllib.request
from hashlib import md5
from urllib import parse
from urllib.parse import urlparse

import requests
from dateutil.parser import parse
from django.conf import settings
from django.core.urlresolvers import reverse
from simple_salesforce import Salesforce
from simple_salesforce.login import SalesforceAuthenticationFailed
from sugarcrm.client import Client as SugarClient
from sugarcrm.exception import BaseError, WrongParameter, InvalidLogin

from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.exceptions.sugarcrm import SugarCRMError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.models import ActionSpecification
from apps.gp.models import StoredData, Webhook



class SugarCRMController(BaseController):
    _user = None
    _password = None
    _url = None
    _client = None
    _module = None

    def __init__(self, *args, **kwargs):
        super(SugarCRMController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(SugarCRMController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._user = self._connection_object.connection_user
                    self._password = self._connection_object.connection_password
                    self._url = self._connection_object.url
                except AttributeError as e:
                    raise SugarCRMError(code=1, msg='Error getting the SugarCRM attributes args. {}'.format(str(e)))
            else:
                raise ControllerError('No connection.')
        try:
            self._module = args[2]
        except Exception as e:
            pass
        if self._url is not None and self._user is not None and self._password is not None:
            try:
                self._client = SugarClient(self._url, self._user, self._password)
            except InvalidLogin as e:
                raise SugarCRMError(code=2, msg='Invalid login. {}'.format(str(e)))

    def test_connection(self):
        return self._client is not None and self._client.session_id is not None

    def get_available_modules(self):
        try:
            return self._client.get_available_modules()
        except BaseError as e:
            raise SugarCRMError(code=3, msg='Error. {}'.format(str(e)))

    def get_entry_list(self, module, **kwargs):
        try:
            return self._client.get_entry_list(module, **kwargs)
        except WrongParameter as e:
            raise SugarCRMError(code=4, msg='Wrong Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise SugarCRMError(code=3, msg='Error. {}'.format(str(e)))

    def get_module_fields(self, module, **kwargs):
        try:
            return self._client.get_module_fields(module, **kwargs)
        except WrongParameter as e:
            raise SugarCRMError(code=4, msg='Wrong Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise SugarCRMError(code=3, msg='Error. {}'.format(str(e)))

    def set_entry(self, module, item):
        try:
            return self._client.set_entry(module, item)
        except WrongParameter as e:
            raise SugarCRMError(code=4, msg='Wrong Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise SugarCRMError(code=3, msg='Error. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, limit=29, order_by="date_entered DESC", **kwargs):
        module = plug.plug_action_specification.get(action_specification__name="module").value
        data = self.get_entry_list(module, max_results=limit, order_by=order_by)
        entries = data['entry_list']
        new_data = []
        for item in entries:
            item['name_value_list'] = self.dictfy(item['name_value_list'])
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                for k, v in item['name_value_list'].items():
                    new_data.append(
                        StoredData(name=k, value=v, object_id=item['id'], connection=connection_object.connection,
                                   plug=plug))
        if new_data:
            field_count = len(entries[0]['name_value_list'])
            extra = {'controller': 'sugarcrm'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                        item.object_id, item.plug.id, item.connection.id), extra=extra)
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            return True
        return False

    def dictfy(self, _dict):
        return {k: v['value'] for k, v in _dict.items()}

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
                except:
                    data_list = []
        if self._plug is not None:
            obj_list = []
            module_name = self._plug.plug_action_specification.all()[0].value
            extra = {'controller': 'sugarcrm'}
            for item in data_list:
                try:
                    res = self.set_entry(module_name, item)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (res['id']), extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (res['id']), extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def get_mapping_fields(self, **kwargs):
        specification = self._plug.plug_action_specification.first()
        module = specification.value
        fields = self.get_module_fields(module)
        import pprint
        pprint.pprint(fields)
        return [MapField(f, controller=ConnectorEnum.SugarCRM) for f in fields['module_fields'].values()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'module':
            data = self.get_available_modules()
            module_list = tuple({'id': m['module_key'], 'name': m['module_key']} for m in data['modules'])
            return module_list
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


class ZohoCRMController(BaseController):
    _token = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(ZohoCRMController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                except Exception as e:
                    print("Error getting zohocrm token")
                    print(e)

    def test_connection(self):
        if self._token is not None:
            response = json.loads(self.get_modules()['_content'].decode())
            if "result" in response["response"]:
                return self._token is not None
        return False

    def get_modules(self):
        params = {'authtoken': self._token, 'scope': 'crmapi'}
        url = "https://crm.zoho.com/crm/private/json/Info/getModules"
        return requests.get(url, params).__dict__

    def download_to_stored_data(
            self,
            connection_object,
            plug, ):
        module_id = self._plug.plug_action_specification.all()[0].value
        module_name = self.get_module_name(module_id)
        data = self.get_feeds(module_name)
        new_data = []
        for item in data:
            q = StoredData.objects.filter(
                connection=connection_object.connection,
                plug=plug,
                object_id=item[item['id']])
            if not q.exists():
                for column in item:
                    new_data.append(
                        StoredData(
                            name=column,
                            value=item[column],
                            object_id=item[item['id']],
                            connection=connection_object.connection,
                            plug=plug))
        if new_data:
            field_count = len(data)
            extra = {'controller': 'zohocrm'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info(
                            'Item ID: %s, Connection: %s, Plug: %s successfully stored.'
                            % (item.object_id, item.plug.id,
                               item.connection.id),
                            extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.'
                        % (item.object_id, item.name, item.plug.id,
                           item.connection.id),
                        extra=extra)
            return True
        return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            module_id = self._plug.plug_action_specification.all()[0].value
            extra = {'controller': 'zohocrm'}
            for item in data_list:
                try:
                    response = self.insert_records(item, module_id)
                    self._log.info(
                        'Item: %s successfully sent.' %
                        (int(response['#text'])),
                        extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info(
                        'Item: %s failed to send.' % (int(response['#text'])),
                        extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, module, **kwargs):
        return self.get_module_fields(module, **kwargs)

    def get_mapping_fields(self):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.ZohoCRM) for f in fields]

    def get_target_fields(self, **kwargs):
        module_id = self._plug.plug_action_specification.all()[0].value
        fields = self.get_fields(module_id)
        return fields

    def get_fields(self, module_id):
        modules = self.get_modules()['_content'].decode()
        modules = json.loads(modules)['response']['result']['row']
        module_name = self.get_module_name(module_id)
        authtoken = self._token
        params = {'authtoken': authtoken, 'scope': 'crmapi'}
        url = "https://crm.zoho.com/crm/private/json/" + module_name + "/getFields"
        response = requests.get(url, params).__dict__
        values = response['_content']
        values = values.decode()
        values = json.loads(values)
        if (module_name in values):
            values = values[module_name]['section']
            fields = []
            for val in values:
                if (type(val['FL']) == dict):
                    fields.append(val['FL'])
                else:
                    for i in val['FL']:
                        fields.append(i)
            return fields
        else:
            print(response)
            print("no_values")

    def get_lists(self, result, name):
        modules = []
        if (type(result) == list):
            for v in result:
                modules.append(self.create_dictionary(v, name))
        else:
            modules.append(self.create_dictionary(result, name))
        return modules

    def create_dictionary(self, my_dictionary, name):
        modules = {}
        if name == "Tasks":
            module_n = "Activity"
        elif name == "PriceBooks":
            module_n = "Book"
        else:
            module_n = name
            module_n = module_n[:-1]
        modules['name'] = name
        modules['id'] = module_n.upper() + 'ID'
        for d in my_dictionary['FL']:
            if ('content' in d):
                modules[d['val']] = d['content']
            else:
                for v2 in d:
                    if (v2 != 'val'):
                        self.get_lists(d[v2], v2)
        return modules

    def get_feeds(self, module_name):
        max_result = 30
        params = {
            'toIndex': 30,
            'authtoken': self._token,
            'scope': 'crmapi',
            'sortOrderString': 'desc'
        }
        url = "https://crm.zoho.com/crm/private/json/" + module_name + "/getMyRecords"
        response = requests.get(url, params).__dict__['_content'].decode()
        response = json.loads(response)
        response = response['response']
        if ("result" in response):
            response = response['result'][module_name]['row']
            modules = self.get_lists(response, module_name)
            return modules
        else:
            print("no hay datos")
            print(response)
        return None

    def get_module_name(self, module_id):
        modules = self.get_modules()['_content'].decode()
        modules = json.loads(modules)['response']['result']['row']
        for m in modules:
            if (m['id'] == module_id):
                if (m['pl'] == "Activities"):
                    module_name = "Tasks"
                else:
                    module_name = m['pl']
        module_name = module_name.replace("-", " ")
        module_name = string.capwords(module_name)
        return module_name.replace(" ", "")

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.filter(
            pk=action_specification_id)
        if action_specification.name.lower() == 'feed':
            modules = self.get_modules()['_content'].decode()
            modules = json.loads(modules)['response']['result']['row']
            module_list = []
            for m in modules:
                if m['pl'] not in [
                    'Feeds', 'Visits', 'Social', 'Documents', 'Quotes',
                    'Sales Orders', 'Purchase Orders'
                ]:
                    module_list.append({'id': m['id'], 'name': m['pl']})
            return tuple(module_list)
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector."
            )


class SalesforceController(BaseController):
    token = None
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(SalesforceController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self.token = self._connection_object.token
                except Exception as e:
                    print("Error getting salesforce attributes")
                    print(e)

    def test_connection(self):
        if self.token is not None:
            try:
                self._client = Salesforce(instance_url=self.get_instance_url(), session_id=self.token)
                self._client = Salesforce(instance_url=self.get_instance_url(), session_id=self.token)
            except SalesforceAuthenticationFailed:
                self._client = None

    def test_connection(self):
        return self._client is not None

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
                success = self.create(obj)
                print(success)
            extra = {'controller': 'bitbucket'}
            return
        raise ControllerError("Incomplete.")

    def download_to_stored_data(self, connection_object=None, plug=None, event=None, **kwargs):
        if event is not None:
            _items = []
            # Todo verificar que este ID siempre existe independiente del action
            event_id = event['new'][0]['Id']
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
                extra = {'controller': 'salesforce'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def create(self, fields):
        birthdate = fields.pop('Birthdate', None)
        if birthdate:
            fields['Birthdate'] = parse(birthdate).strftime('%Y-%m-%d')
        email_bounced_date = fields.pop('EmailBouncedDate', None)
        if email_bounced_date:
            fields['EmailBouncedDate'] = parse(email_bounced_date).strftime(
                '%Y-%m-%dT%H:%M:%S%z')
        last_activity_date = fields.pop('LastActivityDate', None)
        if last_activity_date:
            fields['LastActivityDate'] = parse(last_activity_date).strftime(
                '%Y-%m-%d')
        last_referenced_date = fields.pop('LastReferencedDate', None)
        if last_referenced_date:
            fields['LastReferencedDate'] = parse(last_referenced_date).strftime(
                '%Y-%m-%d')
        last_viewed_date = fields.pop('LastViewedDate', None)
        if last_viewed_date:
            fields['LastViewedDate'] = parse(last_viewed_date).strftime(
                '%Y-%m-%d')
        converted_date = fields.pop('ConvertedDate', None)
        if converted_date:
            fields['ConvertedDate'] = parse(converted_date).strftime('%Y-%m-%d')

        if self._plug.action.name == 'create contact':
            self._client.Contact.create(data=fields)
        else:
            self._client.Lead.create(data=fields)

    def get_contact_meta(self):
        data = self._client.Contact.describe()
        return [
            f for f in data['fields']
            if f['createable'] and f['type'] != 'reference'
        ]

    def get_lead_meta(self):
        data = self._client.Lead.describe()
        return [
            f for f in data['fields']
            if f['createable'] and f['type'] != 'reference'
        ]

    def get_mapping_fields(self):
        fields = self.get_target_fields()
        return [
            MapField(f, controller=ConnectorEnum.Salesforce) for f in fields
        ]

    def get_target_fields(self, **kwargs):
        if self._plug.action.name == 'create contact':
            return self.get_contact_meta()
        else:
            return self.get_lead_meta()

    def user_info_url(self):
        return 'https://login.salesforce.com/services/oauth2/userinfo'

    def headers(self):
        headers = {
            'Accept': 'application/json',
            'Authorization': 'Bearer ' + self.token
        }
        return headers

    def user_info(self):
        r = requests.get(self.user_info_url(), headers=self.headers())
        return r.json()

    def api_url(self, path):
        r = self.user_info()
        path2 = r['urls'].get(path, None)
        if path2:
            return path2.replace('{version}', '40.0')
        return path2

    def rest_url(self):
        return self.api_url('rest')

    def metadata_url(self):
        return self.api_url('metadata')

    def get_objects(self):
        return self.rest_url()

    def get_sobjects(self):
        return requests.get(
            self.rest_url() + 'sobjects', headers=self.headers()).json()

    def create_apex_class(self, name, body):
        _dict = {'ApiVersion': '40.0', 'Body': body, 'Name': name}

        return requests.post(
            self.rest_url() + 'tooling/sobjects/ApexClass',
            headers=self.headers(),
            json=_dict)

    def create_apex_trigger(self, name, body, sobject):
        _dict = {
            'ApiVersion': '40.0',
            'Body': body,
            'Name': name,
            'TableEnumOrId': sobject
        }
        return requests.post(
            self.rest_url() + 'tooling/sobjects/ApexTrigger',
            headers=self.headers(),
            json=_dict)

    def get_apex_triggers(self):
        params = {'q': 'SELECT Name, Body from ApexTrigger'}
        return requests.get(
            self.rest_url() + 'tooling/query',
            headers=self.headers(),
            params=params).json()

    def create_remote_site(self, name, url):
        test = '<env:Envelope xmlns:env="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><env:Header><urn:SessionHeader xmlns:urn="http://soap.sforce.com/2006/04/metadata"><urn:sessionId>{sessionId}</urn:sessionId></urn:SessionHeader></env:Header><env:Body><createMetadata xmlns="http://soap.sforce.com/2006/04/metadata"><metadata xsi:type="RemoteSiteSetting"><fullName>{name}</fullName><isActive>true</isActive><url>{url}</url></metadata></createMetadata></env:Body></env:Envelope>'.replace(
            '{name}', name)
        test = test.replace('{url}', url)
        test = test.replace('{sessionId}', self.token)

        headers = self.headers()
        headers['SOAPAction'] = 'RemoteSiteSetting'
        headers['Content-type'] = 'text/xml'

        return requests.post(self.metadata_url(), headers=headers, data=test)

    def cget_sobject(self):
        _dict = self.get_sobjects()
        return [o['name'] for o in _dict['sobjects'] if o['triggerable']]

    def get_webhook(self):
        _dict = self.get_apex_triggers()

    def create_webhook(self):
        action = self._plug.action.name
        if action == 'new event':
            sobject = self._plug.plug_action_specification.get(action_specification__name='sobject')
            event = self._plug.plug_action_specification.get(action_specification__name='event')
            # Creacion de Webhook
            webhook = Webhook.objects.create(name='salesforce', plug=self._plug, url='', expiration='')
            # Verificar ngrok para determinar url_base
            url_base = 'https://9963f73a.ngrok.io'
            url_path = reverse('home:webhook', kwargs={'connector': 'salesforce', 'webhook_id': webhook.id})
            url = url_base + url_path
            with open(os.path.join(settings.BASE_DIR, 'files', 'Webhook.txt'), 'r') as file:
                body = file.read()
            response1 = self.create_apex_class('Webhook', body)
            if response1.status_code != 201:
                response = response1.json()
                # Si el APEX Class ya existe (es duplicado), continuamos, si es otro error, paramos
                print(response[0]['errorCode'])
                print(response[0]['errorCode'] != 'DUPLICATE_VALUE')
                if 'errorCode' in response[0] and response[0]['errorCode'] == 'DUPLICATE_VALUE':
                    pass
                else:
                    return False

            response2 = self.create_remote_site('GearPlug' + 'RemoteSiteSetting{}'.format(webhook.id), url)
            if response2.status_code != 200:
                return False

            with open(os.path.join(settings.BASE_DIR, 'files', 'WebhookTrigger.txt'), 'r') as file:
                body = file.read()

            body = body.replace('{name}', 'GearPlug{}'.format(webhook.id))
            body = body.replace('{sobject}', sobject.value)
            body = body.replace('{events}', event.value)
            body = body.replace('{url}', "'" + url + "'")

            apex_trigger = self.create_apex_trigger('GearPlug', body, 'User')
            if apex_trigger.status_code == 201:
                webhook.url = url_base + url_path
                webhook.generated_id = apex_trigger.json()['id']
                webhook.is_active = True
                webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True
        return False

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() in ['sobject']:
            tup = tuple({'id': p, 'name': p} for p in self.get_sobject_list())
            return tup
        if action_specification.name.lower() in ['event']:
            tup = tuple({'id': p, 'name': p} for p in self.get_event_list())
            return tup
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def get_sobject_list(self):
        return self.cget_sobject()

    def get_event_list(self):
        return [
            'before insert', 'before update', 'before delete', 'after insert',
            'after update', 'after delete', 'after undelete'
        ]

    def get_instance_url(self):
        o = urlparse(self.api_url('profile'))
        return o.scheme + '://' + o.netloc

    def get_specifications_values(self):
        sobject = None
        event = None
        for specification in self._plug.plug_specification.all():
            if specification.action_specification.name == 'SObject':
                sobject = specification.value
            elif specification.action_specification.name == 'Event':
                event = specification.value
        return sobject, event

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'order by':
            return tuple({'id': c['name'], 'name': c['name']} for c in self.describe_table())
        elif action_specification.name.lower() == 'unique':
            return tuple({'id': c['name'], 'name': c['name']} for c in self.describe_table())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


class HubSpotController(BaseController):
    _token = None
    _refresh_token = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(HubSpotController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._refresh_token = self._connection_object.refresh_token
                except Exception as e:
                    print("Error getting the hubspot token")

    def test_connection(self):
        response = self.request()
        if 'status' in response and response['status'] == "error":
            self.get_refresh_token(self._refresh_token)
        return self._token is not None

    def get_modules(self):
        return [{
            'name': 'companies',
            'id': 'companies'
        }, {
            'name': 'contacts',
            'id': 'contacts'
        }, {
            'name': 'deals',
            'id': 'deals'
        }]

    def get_action_specification_options(self, action_specification_id):
        print("actions")
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'data':
            return tuple({
                             'name': o['name'],
                             'id': o['id']
                         } for o in self.get_modules())
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector."
            )

    def download_to_stored_data(
            self,
            connection_object,
            plug, ):
        module_id = self._plug.plug_action_specification.all()[0].value
        new_data = []
        data = self.get_data(module_id)
        for item in data:
            q = StoredData.objects.filter(
                connection=connection_object.connection,
                plug=plug,
                object_id=item['id'])
            if not q.exists():
                for column in item:
                    new_data.append(
                        StoredData(
                            name=column,
                            value=item[column],
                            object_id=item['id'],
                            connection=connection_object.connection,
                            plug=plug))
        if new_data:
            field_count = len(data)
            extra = {'controller': 'hubspot'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info(
                            'Item ID: %s, Connection: %s, Plug: %s successfully stored.'
                            % (item.object_id, item.plug.id,
                               item.connection.id),
                            extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.'
                        % (item.object_id, item.name, item.plug.id,
                           item.connection.id),
                        extra=extra)
            return True
        return False

    def get_data(self, module_id):
        if (module_id == 'contacts'):
            url = "https://api.hubapi.com/contacts/v1/lists/all/contacts/all"
        if (module_id == 'companies'):
            url = "https://api.hubapi.com/companies/v2/companies/"
        if (module_id == 'deals'):
            url = "https://api.hubapi.com/deals/v1/deal/paged?includeAssociations=true&limit=30&properties=dealname"
        headers = {
            'Authorization': 'Bearer {0}'.format(self._token),
        }
        result = requests.get(url, headers=headers).json()[module_id]
        data = []
        for i in result:
            item = {}
            id = self.get_id(module_id, i)
            item['id'] = id
            for d in i["properties"]:
                item[d] = i["properties"][d]['value']
            data.append(item)
        return data

    def get_mapping_fields(self):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.HubSpot) for f in fields]

    def get_target_fields(self, **kwargs):
        module_id = self._plug.plug_action_specification.all()[0].value
        url = "https://api.hubapi.com/properties/v1/" + module_id + "/properties"
        headers = {'Authorization': 'Bearer {0}'.format(self._token)}
        response = requests.get(url, headers=headers).json()
        return [
            i for i in response if "label" in i and i['readOnlyValue'] == False
        ]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            module_id = self._plug.plug_action_specification.all()[0].value
            extra = {'controller': 'hubspot'}
            for item in data_list:
                try:
                    response = self.insert_data(item, module_id).json()
                    id = self.get_id(module_id, response)
                    self._log.info(
                        'Item: %s successfully sent.' % (id), extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info(
                        'Item: %s failed to send.' % (id), extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def insert_data(self, fields, module_id):
        if (module_id == 'contacts'):
            url = "https://api.hubapi.com/contacts/v1/contact/"
            name = "property"
        if (module_id == 'companies'):
            url = "https://api.hubapi.com/companies/v2/companies/"
            name = "name"
        if (module_id == 'deals'):
            url = "https://api.hubapi.com/deals/v1/deal"
            name = "name"
        headers = {'Authorization': 'Bearer {0}'.format(self._token)}
        list = []
        for i in fields:
            write = {name: i, 'value': fields[i]}
            list.append(write)
        json = {"properties": list}
        return requests.post(url, json=json, headers=headers)

    def get_id(self, module_id, data):
        if (module_id == 'contacts'):
            id = data['vid']
        if (module_id == 'companies'):
            id = data['companyId']
        if (module_id == 'deals'):
            id = data['dealId']
        return id

    def get_refresh_token(self, refresh_token):
        url = "https://api.hubapi.com/oauth/v1/token"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'charset': 'utf-8'
        }
        data = {
            'grant_type': 'refresh_token',
            'client_id': settings.HUBSPOT_CLIENT_ID,
            'client_secret': settings.HUBSPOT_CLIENT_SECRET,
            'redirect_uri': settings.HUBSPOT_REDIRECT_URI,
            'refresh_token': self._refresh_token
        }
        response = requests.post(url, headers=headers, data=data).json()
        self._connection_object.token = response['access_token']
        self._connection_object.refresh_token = response['refresh_token']
        self._connection_object.save()
        return None

    def request(self):
        url = "https://api.hubapi.com/contacts/v1/lists/all/contacts/all"
        headers = {
            'Authorization': 'Bearer {0}'.format(self._token),
        }
        return requests.get(url, headers=headers).json()


class VtigerController(BaseController):
    _url = None
    _token = None
    _session_name = None
    _user_id = None

    def __init__(self, *args, **kwargs):
        super(VtigerController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(VtigerController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._user = self._connection_object.connection_user
                    self._password = self._connection_object.connection_access_key
                    self._url = self._connection_object.url
                    self._token = self._connection_object.token
                except Exception as e:
                    print(e)
        if self._url is not None and self._token is not None:
            if not self._token:
                self._token = self.get_token(self._user, self._password)
            self._session_name, self._user_id = self.login()
            if self._session_name is None:
                self._token = self.get_token(self._user, self._password)
                self._session_name, self._user_id = self.login()

    def test_connection(self):
        return self._session_name is not None

    def get_token(self, user, passwd, url=None):
        if self._url is None and url is not None:
            self._url = url
        if self._url is not None:
            try:
                values = {'operation': 'getchallenge', 'username': user}
                r = requests.get(self._url, params=values)
                if r.status_code == 200:
                    r = r.json()
                    return r['result']['token']
                return None
            except Exception as e:
                print(e)
                return None

    def get_tokenized_access_key(self):
        try:
            return md5(
                str(self._token + self._password).encode('utf-8')).hexdigest()
        except Exception as es:
            return None

    def login(self):
        try:
            tokenized_access_key = self.get_tokenized_access_key()
            values = {'accessKey': tokenized_access_key, 'operation': 'login', 'username': self._user}
            data = urllib.parse.urlencode(values).encode('utf-8')
            request = urllib.request.Request(self._url, data)
            response = json.loads(urllib.request.urlopen(request).read().decode('utf-8'))
            if response['success'] is True:
                session_name = response['result']['sessionName']
                user_id = response['result']['userId']
                return session_name, user_id
            elif response['success'] is False:
                return None, None
        except Exception as e:
            raise

    def get_module(self, module_name):
        values = {'sessionName': self._session_name, 'operation': 'describe', 'elementType': module_name}
        r = requests.get(self._url, params=values)
        if r.status_code == 200:
            r = r.json()
            return {'name': module_name, 'id': r['result']['idPrefix']}
        raise Exception("Error retrieving module data.")

    def get_modules(self):
        try:
            values = {
                'sessionName': self._session_name,
                'operation': 'listtypes'
            }
            r = requests.get(self._url, params=values)
            if r.status_code == 200:
                r = r.json()
                modules = []
                if r['success'] == True:
                    for key in r['result']['information']:
                        modules.append(self.get_module(key))
                return modules
            return []
        except Exception as e:
            raise
            return (e)

    def get_module_elements(self, module=None, limit=30):
        query = "select * from {0} order by createdtime desc;".format(module)
        values = {'sessionName': self._session_name, 'operation': 'query', 'query': query}
        r = requests.get(self._url, params=values).json()
        try:
            data = r['result']
            return data
        except Exception as e:
            print(e)
            return []

    def create_register(self, module, **kwargs):

        kwargs['assigned_user_id'] = self._user_id
        for k, v in kwargs.items():
            try:
                kwargs[k] = (self.get_module(v)["id"])
            except Exception as e:
                continue

        kwargs['elementType'] = module
        parameters = {
            'operation': 'create',
            'sessionName': self._session_name,
            'elementType': kwargs['elementType'],
            'element': json.dumps(kwargs)
        }

        parameters = urllib.parse.urlencode(parameters)
        connection = urllib.request.urlopen(self._url, parameters.encode('utf-8'))
        response = connection.read().decode('utf-8')
        response = json.loads(response)
        if response['success'] is True:
            return response
        else:
            return False

    def delete_register(self):
        """
        Not implemented Yet.
        :return:
        """
        session_name, user_id = self.login()
        parameters = {
            'operation': 'delete',
            'sessionName': session_name,
            'id': id
        }
        session_name = parameters['sessionName']

        parameters = urllib.parse.urlencode(parameters)
        connection = urllib.request.urlopen(self._url, parameters.encode('utf-8'))
        response = connection.read().decode('utf-8')
        response = json.loads(response)
        return response

    def get_module_name(self, module_id):
        try:
            for module in self.get_modules():
                if module['id'] == module_id:
                    return module['name']
        except Exception as e:
            print(e)

    def get_module_fields(self, module_name):
        try:
            details = {
                'operation': 'describe',
                'sessionName': self._session_name,
                'elementType': str(module_name)
            }
            response = requests.get(self._url, params=details).json()
            module_fields = []
            for i in response['result']['fields']:
                module_fields.append(i)
            return module_fields
        except Exception as e:
            print(e)

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        try:
            if action_specification.name.lower() == 'module':
                return tuple(self.get_modules())
            else:
                raise ControllerError(
                    "That specification doesn't belong to an action in this connector."
                )
        except Exception as e:
            print(e)

    def download_to_stored_data(self, connection_object, plug=None):
        module_id = self._plug.plug_action_specification.get(action_specification__name__iexact='module').value
        data = self.get_module_elements(limit=30, module=self.get_module_name(module_id))
        new_data = []
        for field in data:
            q = StoredData.objects.filter(
                object_id=field['id'],
                connection=connection_object.connection,
                plug=plug)

            if not q.exists():
                for k, v in field.items():
                    new_data.append(
                        StoredData(
                            name=k,
                            value=v or '',
                            object_id=field['id'],
                            connection=connection_object.connection,
                            plug=plug))
        if new_data:
            field_count = len(data)
            extra = {'controller': 'vtiger'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info(
                            'Item ID: %s, Connection: %s, Plug: %s successfully stored.'
                            % (item.object_id, item.plug.id,
                               item.connection.id),
                            extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.'
                        % (item.object_id, item.name, item.plug.id,
                           item.connection.id),
                        extra=extra)
            return True
        return False

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Vtiger) for f in fields]

    def get_target_fields(self, **kwargs):
        module_id = self._plug.plug_action_specification.get(
            action_specification__name__iexact='module').value
        module_fields = (self.get_module_fields(self.get_module_name(module_id)))
        fields_list = []
        for i in module_fields:
            if i['editable'] is True:
                fields_list.append(i)
        if len(fields_list) > 0:
            return fields_list
        else:
            return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'Vtiger'}
            module_id = self._plug.plug_action_specification.get(
                action_specification__name__iexact='module').value
            module_name = self.get_module_name(module_id)
            for item in data_list:
                task = self.create_register(module_name, **item)
                try:
                    if task['success'] is True:
                        extra['status'] = 's'
                        self._log.info(
                            'Item: %s successfully sent.' % (task),
                            extra=extra)
                        obj_list.append(task)
                    else:
                        extra['status'] = 'f'
                        self._log.info('Item: failed to send.', extra=extra)
                except Exception as e:
                    print(e)
            return obj_list
        raise ControllerError("There's no plug")


class ActiveCampaignController(BaseController):
    _host = None
    _key = None

    def __init__(self, *args, **kwargs):
        super(ActiveCampaignController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(ActiveCampaignController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._host = self._connection_object.host
                    self._key = self._connection_object.connection_access_key
                except Exception as e:
                    print(e)

    def get_account_info(self):
        self.create_connection()
        params = [
            ('api_action', "account_view"),
            ('api_key', self._key),
            ('api_output', 'json'),
        ]
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.get(url=final_url, params=params)
        if r.status_code == 200:
            return True
        else:
            return False

    def get_lists(self):
        params = [
            ('api_action', "list_list"),
            ('api_key', self._key),
            ('ids', "all"),
            ('api_output', 'json'),
            ('full', 0)
        ]
        final_url = "{0}/admin/api.php".format(self._host)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.get(url=final_url, params=params, headers=headers)
        lists = r.json()

        # Se retorna result porque la data relevante se encuentra mismo
        # nivel que data no relevante.
        result = []
        if lists['result_code'] == 1:
            for k, v in lists.items():
                if type(v) == dict:
                    result.append(v)
        return result

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        try:
            if action_specification.name.lower() == 'lists':
                for i in self.get_lists():
                    return tuple({'id': i['id'], 'name': i['name']} for i in self.get_lists())
            else:
                raise ControllerError(
                    "That specification doesn't belong to an action in this connector."
                )
        except Exception as e:
            print(e)

    def test_connection(self):
        try:
            return self.get_account_info() is True
        except:
            return False

    def create_webhook(self):
        action = self._plug.action.name
        if action == 'Detect contact creation':
            selected_list = self._plug.plug_action_specification.get(
                action_specification__name='lists')

            # Creacion de Webhook
            webhook = Webhook.objects.create(name='activecampaign', plug=self._plug,
                                             url='', expiration='')

            # Verificar ngrok para determinar url_base
            # url_base = 'https://e0ae5cfd.ngrok.io'
            url_base = settings.CURRENT_HOST
            url_path = reverse('home:webhook',
                               kwargs={'connector': 'activecampaign',
                                       'webhook_id': webhook.id})
            url = url_base + url_path
            params = [
                ('api_action', "webhook_add"),
                ('api_key', self._key),
                ('api_output', 'json'),
            ]
            post_array = {
                "name": "GearPlug WebHook",
                "url": url,
                "lists": selected_list,
                "action": "subscribe",
                "init": "admin"
            }
            final_url = "{0}/admin/api.php".format(self._host)
            r = requests.post(url=final_url, data=post_array, params=params)
            if r.status_code == 201:
                webhook.url = url_base + url_path
                webhook.generated_id = r.json()['id']
                webhook.is_active = True
                webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True
        return False

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [
            MapField(f, controller=ConnectorEnum.ActiveCampaign) for f in fields
        ]

    def get_target_fields(self, **kwargs):
        return [{'name': 'email', 'type': 'varchar', 'required': True},
                {'name': 'first_name', 'type': 'varchar', 'required': False},
                {'name': 'last_name', 'type': 'varchar', 'required': False},
                {'name': 'phone', 'type': 'varchar', 'required': False},
                {'name': 'orgname', 'type': 'varchar', 'required': False},
                ]

    def create_user(self, data):
        params = [
            ('api_action', "contact_sync"),
            ('api_key', self._key),
            ('api_output', 'json'),
        ]
        data=data
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, data=data, params=params).json()
        return r

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)

        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'activecampaign'}
            for item in data_list:
                try:
                    response = self.create_user(item)
                    self._log.info(
                        'Item: %s successfully sent.' % (list(item.items())[0][1]),
                        extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info(
                        'Item: %s failed to send.' % (list(item.items())[0][1]),
                        extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def download_to_stored_data(self, connection_object=None, plug=None, data=None, **kwargs):
        new_data = []
        if data is not None:
            object_id = int(data['contact[id]'])
            q = StoredData.objects.filter(object_id=object_id, connection=connection_object.id, plug=plug.id)
            if not q.exists():
                for k, v in data.items():
                    new_data.append(StoredData(name=k, value=v or '', object_id=object_id, connection=connection_object.connection, plug=plug))
            if new_data:
                field_count = len(data)
                extra = {'controller': 'activecampaign'}
                for i, item in enumerate(new_data):
                    try:
                        item.save()
                        if (i + 1) % field_count == 0:
                            extra['status'] = 's'
                            self._log.info(
                                'Item ID: %s, Connection: %s, Plug: %s successfully stored.'
                                % (item.object_id, item.plug.id,
                                   item.connection.id),
                                extra=extra)
                    except Exception as e:
                        print(e)
                        extra['status'] = 'f'
                        self._log.info(
                            'Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.'
                            % (item.object_id, item.name, item.plug.id,
                               item.connection.id),
                            extra=extra)
            return True
        return False