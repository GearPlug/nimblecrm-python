from django.conf import settings
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.models import StoredData, ActionSpecification, HubSpotConnection, VtigerConnection
from simple_salesforce import Salesforce
from simple_salesforce.login import SalesforceAuthenticationFailed
from dateutil.parser import parse
from urllib.parse import urlparse
from hashlib import md5
import urllib.error
import urllib.request
import requests
import sugarcrm
import json
import xmltodict
import string
import os
from apps.gp.models import StoredData
from apps.gp.map import MapField
from apps.gp.enum import ConnectorEnum
import xml.etree.ElementTree as ET
from django.conf import settings


class CustomSugarObject(sugarcrm.SugarObject):
    module = "CustomObject"

    def __init__(self, *args, **kwargs):
        if args:
            self.module = args[0]
        return super(CustomSugarObject, self).__init__(**kwargs)

    @property
    def query(self):
        return ''


class SugarCRMController(BaseController):
    _user = None
    _password = None
    _url = None
    _session = None
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
                except Exception as e:
                    print("Error getting the SugarCRM attributes")
                try:
                    self._module = args[2]
                except:
                    pass
        if self._url is not None and self._user is not None and self._password is not None:
            self._session = sugarcrm.Session(self._url, self._user,
                                             self._password)

    def test_connection(self):
        return self._session is not None and self._session.session_id is not None

    def get_available_modules(self):
        return self._session.get_available_modules()

    def get_entries(self, module_name, id_list):
        return self._session.get_entries(module_name, id_list)

    def get_entry_list(self, module, **kwargs):
        custom_module = CustomSugarObject(module)
        return self._session.get_entry_list(custom_module, **kwargs)

    def get_module_fields(self, module, **kwargs):
        custom_module = CustomSugarObject(module)
        return self._session.get_module_fields(custom_module, **kwargs)

    def set_entry(self, obj):
        return self._session.set_entry(obj)

    def set_entries(self, obj_list):
        return self._session.set_entries(obj_list)

    def download_to_stored_data(self,
                                connection_object,
                                plug,
                                limit=29,
                                order_by="date_entered DESC",
                                **kwargs):
        print("descargando mierda")
        module = plug.plug_action_specification.get(
            action_specification__name="module"
        ).value  # Especificar que specification
        print("module", module)
        data = self.get_entry_list(module, max_results=limit, order_by=order_by)
        new_data = []
        print('data', data)
        for item in data:
            q = StoredData.objects.filter(
                connection=connection_object.connection,
                plug=plug,
                object_id=item.id)
            if not q.exists():
                for column in item.fields:
                    new_data.append(
                        StoredData(
                            name=column['name'],
                            value=column['value'],
                            object_id=item.id,
                            connection=connection_object.connection,
                            plug=plug))
        if new_data:
            field_count = len(data[0].fields)
            extra = {'controller': 'sugarcrm'}
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
                    res = self.set_entry(CustomSugarObject(module_name, **item))
                    extra['status'] = 's'
                    self._log.info(
                        'Item: %s successfully sent.' % (res.id), extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info(
                        'Item: %s failed to send.' % (res.id), extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def get_mapping_fields(self, **kwargs):
        specification = self._plug.plug_action_specification.first()
        module = specification.value
        fields = self.get_module_fields(module, get_structure=True)
        return [MapField(f, controller=ConnectorEnum.SugarCRM) for f in fields]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'module':
            module_list = tuple({
                'id': m.module_key,
                'name': m.module_key
            } for m in self.get_available_modules())
            return module_list
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector."
            )


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
            plug,):
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
        elif kwargs:
            try:
                self.token = kwargs.pop('token', None)
            except Exception as e:
                print("Error getting salesforce attributes")
                print(e)
        if self.token is not None:
            try:
                instance_url = self.get_instance_url()
                self._client = Salesforce(
                    instance_url=instance_url, session_id=self.token)
            except SalesforceAuthenticationFailed:
                self._client = None
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

    def download_to_stored_data(self,
                                connection_object=None,
                                plug=None,
                                event=None,
                                **kwargs):
        if event is not None:
            _items = []
            # media es un objecto, se debe convertir a diccionario:
            _dict = event.__dict__
            q = StoredData.objects.filter(
                connection=connection_object.connection,
                plug=plug,
                object_id=event.id)
            if not q.exists():
                for k, v in _dict.items():
                    obj = StoredData(
                        connection=connection_object.connection,
                        plug=plug,
                        object_id=event.id,
                        name=k,
                        value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'salesforce'}
                self._log.info(
                    'Item ID: %s, Connection: %s, Plug: %s successfully stored.'
                    % (item.object_id, item.plug.id, item.connection.id),
                    extra=extra)
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

    # tree = ET.parse('remote_site.xml')
    # print(tree)
    # print(ET.tostring(tree.getroot(), encoding='utf8', method='xml'))

    # controlador

    def cget_sobject(self):
        _dict = self.get_sobjects()
        return [o['name'] for o in _dict['sobjects'] if o['triggerable']]

    def get_webhook(self):
        _dict = self.get_apex_triggers()

    def create_webhook(self):
        body = None
        with open(os.path.join(settings.BASE_DIR, 'files', 'Webhook.txt'),
                  'r') as file:
            body = file.read()

        apex_class = self.create_apex_class('Webhook', body)
        print(apex_class.text)

        remote_site_site = self.create_remote_site(
            'GearPlug' + 'RemoteSiteSetting', settings.SALESFORCE_WEBHOOK_URI)
        print(remote_site_site.text)

        body = None
        with open(
                os.path.join(settings.BASE_DIR, 'files', 'WebhookTrigger.txt'),
                'r') as file:
            body = file.read()

        sobject, event = self.get_specifications_values()

        body = body.replace('{name}', 'GearPlug')
        body = body.replace('{sobject}', sobject)
        body = body.replace('{events}', event)
        body = body.replace('{url}',
                            "'" + settings.SALESFORCE_WEBHOOK_URI + "'")

        apex_trigger = self.create_apex_trigger('GearPlug', body, 'User')
        print(apex_trigger.text)

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
            plug,):
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
    _user = None
    _password = None
    _url = None
    _token = None
    _values = None
    _session = None
    _module = None
    _module_list = None
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
                    self._url = '%s/webservice.php' % self._connection_object.url
                except Exception as e:
                    print("Error getting the Vtiger attributes", e)
                try:
                    self._module = args[2]
                except:
                    pass
        if self._url is not None and self._user is not None and self._password is not None:
            if self.get_token() is True:
                self.login()

    def test_connection(self):
        return self._values is not None

    def get_token(self):
        try:
            self._values = {'operation': 'getchallenge', 'username': self._user}
            data = urllib.parse.urlencode(self._values)

            req = urllib.request.Request('%s?%s' % (self._url, data))
            response = urllib.request.urlopen(req).read()
            token = json.loads(response.decode('utf-8'))['result']['token']
            self._token = token
            int("Table Token >> ", table_token)
            obj = VtigerConnection.objects.filter(
                connection_id=self._connection_object.connection.id).update(
                    token=self._token)
            return True
        except Exception as e:
            print(e)
            return False

    def login(self):
        try:
            # self._token, self._password, self._values = self.get_token()
            access_and_token = self._token + self._password
            access_and_token = access_and_token.encode('utf-8')
            tokenized_access_key = md5(access_and_token).hexdigest()
            self._values['accessKey'] = tokenized_access_key
            self._values['operation'] = 'login'

            data = urllib.parse.urlencode(self._values)
            data = data.encode('utf-8')
            req = urllib.request.Request(self._url, data)
            response = urllib.request.urlopen(req)
            response = (response.read()).decode('utf-8')
            response = json.loads(response)
            if response['success']:
                self._values["sessionName"] = response['result']['sessionName']
                user_id = response['result']['userId']
                return self._values["sessionName"], user_id
        except Exception as e:
            print("Problemas durante el login: ", e)

    def extend_session(self):
        print("EXTENDING SESSION")
        response = requests.post('{0}?sessionName={1}&operation=extendsession'.
                                 format(self._url, self._values['sessionName']))
        pass

    def get_modules_info(self):
        """
        Metodo que devuelve una lista de las entidades del CRM y los campos de
        dichas entidades.
        :return:
        """
        self._module_dict = {}
        try:
            self._session_name, self._user_id = self.login()
            req = urllib.request.Request(
                "{0}?operation=listtypes&sessionName={1}".format(
                    self._url, self._session_name))
            response = urllib.request.urlopen(req)
            response = (response.read()).decode('utf-8')
            response2 = json.loads(response)
            mod_ids = []
            mod_names = []
            for k2, v2 in response2['result']['information'].items():
                req = urllib.request.Request(
                    "{0}?operation=describe&sessionName={1}&elementType={2}"
                    .format(self._url, self._session_name, k2))
                response = urllib.request.urlopen(req)
                response = (response.read()).decode('utf-8')
                response = json.loads(response)
                mod_names.append({k2: response['result']['idPrefix']})
            self._module_dict = mod_names
            return (self._module_dict)
        except Exception as e:
            return (e)


    def query_last(self, last, entity):
        self._session_name, self._user_id = self.login()

        query = "select * from {0} order by createdtime desc;".format(entity)
        parameters = {
            'operation': 'query',
            'session_name': self._session_name,
            'query': query
        }

        url_query = '%s?operation=query&sessionName=%s&query=%s' % (
            self._url, parameters['session_name'], parameters['query'])
        response = requests.get(url_query)
        response = response.content.decode('utf-8')
        response = json.loads(response)
        data = []
        try:
            for i in range(len(response)):
                data.append(response['result'][i])
            return data
        except Exception as e:
            if e == IndexError:
                return data
            else:
                print("Error En Consulta >> ", e)


    def get_module_name(self, module_id):
        try:
            modules_list = self.get_modules_info()
            for i in modules_list:
                for k, v in i.items():
                    if v == module_id:
                        module_name = k
                        return module_name
        except Exception as e:
            print("Error Obteniendo Nombre de modulo >>", e)
        
        # Detalles de Modulo.
        # try:
        #     details = {
        #         'operation': 'describe',
        #         'sessionName': self._values["sessionName"],
        #         'elementType': str(module_name)
        #     }
        #     response = requests.get(
        #         'http://192.168.10.217/webservice.php?', params=details).json()
        #     module_fields = []
        #     for i in response['result']['fields']:
        #         module_fields.append(i)
        #     return module_fields
        # except Exception as e:
        #     print("Error Obteniendo Specs de Modulo >>", e)

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        options = self.get_modules_info()
        select = []
        try:
            if action_specification.name.lower() == 'modulo':
                return tuple({
                    'name': k,
                    'id': v
                } for option in options for k, v in option.items())
            else:
                raise ControllerError(
                    "That specification doesn't belong to an action in this connector."
                )
        except Exception as e:
            print('ERROR >> ', e)

    def download_to_stored_data(self, connection_object, plug=None):
        if plug is None:
            plug = self._plug

        module_id = self._plug.plug_action_specification.all()[0].value
        new_data = []
        module_name = self.get_module_name(module_id)
        data = self.query_last(10, module_name)
        import pprint
        pprint.pprint(data)

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
                           item.connection.id),extra=extra)
            return True
        return False
