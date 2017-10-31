from hashlib import md5
from urllib.parse import urlparse
from dateutil.parser import parse
from django.core.urlresolvers import reverse
from django.db.models import Q
from simple_salesforce import Salesforce
from simple_salesforce.login import SalesforceAuthenticationFailed
from sugarcrm.client import Client as SugarClient
from sugarcrm.exception import BaseError, WrongParameter, InvalidLogin
from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import ActionSpecification, Plug, PlugActionSpecification, StoredData, Webhook
from apps.gp.map import MapField
from apps.gp.enum import ConnectorEnum
from django.conf import settings
from django.http import HttpResponse
from odoocrm.client import Client as OdooCRMClient
import time
import requests
import re
import json
import os
import string
import base64
import urllib.error
import urllib.request


class SugarCRMController(BaseController):
    _user = None
    _password = None
    _url = None
    _client = None
    _module = None
    __url_end = 'service/v4_1/rest.php'

    def __init__(self, connection=None, plug=None, **kwargs):
        super(SugarCRMController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(SugarCRMController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._user = self._connection_object.connection_user
                self._password = self._connection_object.connection_password
                self._url = self._connection_object.url
                if not self._url.endswith('/service/v4_1/rest.php'):
                    if not self._connection_object.url.endswith('/'):
                        self._url += '/'
                self._url += 'service/v4_1/rest.php'
                try:
                    self._module = self._plug.plug_action_specification.get(
                        action_specification__name__iexact='module').value
                except AttributeError as e:
                    print("No module found. If this is a test_connection ignore the following message."
                          " \nMessage: {0}".format(str(e)))
            except AttributeError as e:
                raise ControllerError(code=1, controller=ConnectorEnum.SugarCRM,
                                      message='Error getting the SugarCRM attributes args. {}'.format(str(e)))
        else:
            raise ControllerError('No connection.')
        if self._url is not None and self._user is not None and self._password is not None:
            try:
                session = requests.Session()
                self._client = SugarClient(self._url, self._user, self._password, session=session)
            except requests.exceptions.MissingSchema:
                raise
            except InvalidLogin as e:
                raise ControllerError(code=2, controller=ConnectorEnum.SugarCRM,
                                      message='Invalid login. {}'.format(str(e)))

    def test_connection(self):
        return self._client is not None and self._client.session_id is not None

    def get_available_modules(self):
        try:
            return self._client.get_available_modules()
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.SugarCRM, message='Error. {}'.format(str(e)))

    def get_entry_list(self, module, **kwargs):
        try:
            return self._client.get_entry_list(module, **kwargs)
        except WrongParameter as e:
            raise ControllerError(code=4, controller=ConnectorEnum.SugarCRM,
                                  message='Wrong Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.SugarCRM,
                                  message='Error. {}'.format(str(e)))

    def get_module_fields(self, module, **kwargs):
        try:
            return self._client.get_module_fields(module, **kwargs)
        except WrongParameter as e:
            raise ControllerError(code=4, controller=ConnectorEnum.SugarCRM, message='Bad Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.SugarCRM, message='Error. {}'.format(str(e)))

    def set_entry(self, module, item):
        try:
            return self._client.set_entry(module, item)
        except WrongParameter as e:
            raise ControllerError(code=4, controller=ConnectorEnum.SugarCRM,
                                  message='Wrong Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.SugarCRM, message='Error. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, limit=49, order_by="date_entered DESC", query='',
                                last_source_record=None, **kwargs):

        """
            NOTE: Se ordena por el campo: 'date_entered'.
        :param connection_object:
        :param plug:
        :param limit:
        :param order_by:
        :param query:
        :param last_source_record:
        :param kwargs:
        :return:
        """
        if last_source_record is not None:
            if query.isspace() or query == '':
                query = "{0}.date_entered > '{1}'".format(self._module.lower(), last_source_record)
            else:
                query += " AND {0}.date_entered > '{1}'".format(self._module.lower(), last_source_record)
        entries = self.get_entry_list(self._module, max_results=limit, order_by=order_by, query=query)['entry_list']
        raw_data = []
        new_data = []
        for item in entries:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                item_data = []
                obj_raw = self.dictfy(item['name_value_list'])
                for k, v in obj_raw.items():
                    if isinstance(v, str) and v.isspace():
                        obj_raw[k] = ''
                for k, v in obj_raw.items():
                    item_data.append(StoredData(name=k, value=v or '', object_id=item['id'],
                                                connection=connection_object.connection, plug=plug))
                raw_data.append(obj_raw)
                new_data.append(item_data)
        if new_data:
            result_list = []
            for item in new_data:
                for stored_data in item:
                    try:
                        stored_data.save()
                    except Exception as e:
                        is_stored = False
                        break
                    is_stored = True
                obj_raw = "RAW DATA NOT FOUND."
                for obj in raw_data:
                    if stored_data.object_id == obj['id']:
                        obj_raw = obj
                        break
                raw_data.remove(obj_raw)
                result_list.append({'identifier': {'name': 'id', 'value': stored_data.object_id},
                                    'is_stored': is_stored, 'raw': obj_raw, })
            return {'downloaded_data': result_list, 'last_source_record': result_list[0]['raw']['date_entered']}
        return False

    def dictfy(self, _dict):
        return {k: v['value'] for k, v in _dict.items()}

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                res = self.set_entry(self._module, item)
                obj_result['response'] = res
                obj_result['sent'] = True
                obj_result['identifier'] = res['id']
            except Exception as e:
                obj_result['response'] = str(e)
                obj_result['sent'] = False
                obj_result['identifier'] = '-1'
            obj_list.append(obj_result)
        return obj_list

    def get_mapping_fields(self, **kwargs):
        fields = self.get_module_fields(self._module)
        return [MapField(f, controller=ConnectorEnum.SugarCRM) for f in fields['module_fields'].values()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'module':
            return tuple({'id': m['module_key'], 'name': m['module_label']}
                         for m in self.get_available_modules()['modules'] if m['module_key'] != 'Home')
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

    def download_to_stored_data(self, connection_object, plug, ):
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
                self._client = Salesforce(instance_url=self.get_instance_url(),
                                          session_id=self.token)
                self._client = Salesforce(instance_url=self.get_instance_url(),
                                          session_id=self.token)
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

    def download_to_stored_data(self, connection_object=None, plug=None,
                                event=None, **kwargs):
        if event is not None:
            _items = []
            # Todo verificar que este ID siempre existe independiente del action
            event_id = event['new'][0]['Id']
            q = StoredData.objects.filter(
                connection=connection_object.connection, plug=plug,
                object_id=event_id)
            if not q.exists():
                for k, v in event.items():
                    obj = StoredData(connection=connection_object.connection,
                                     plug=plug,
                                     object_id=event_id, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'salesforce'}
                self._log.info(
                    'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                        item.object_id, item.plug.id, item.connection.id),
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
            fields['LastReferencedDate'] = parse(
                last_referenced_date).strftime(
                '%Y-%m-%d')
        last_viewed_date = fields.pop('LastViewedDate', None)
        if last_viewed_date:
            fields['LastViewedDate'] = parse(last_viewed_date).strftime(
                '%Y-%m-%d')
        converted_date = fields.pop('ConvertedDate', None)
        if converted_date:
            fields['ConvertedDate'] = parse(converted_date).strftime(
                '%Y-%m-%d')

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
            sobject = self._plug.plug_action_specification.get(
                action_specification__name='sobject')
            event = self._plug.plug_action_specification.get(
                action_specification__name='event')
            # Creacion de Webhook
            webhook = Webhook.objects.create(name='salesforce',
                                             plug=self._plug, url='',
                                             expiration='')
            # Verificar ngrok para determinar url_base
            url_base = settings.WEBHOOK_HOST
            url_path = reverse('home:webhook',
                               kwargs={'connector': 'salesforce',
                                       'webhook_id': webhook.id})
            url = url_base + url_path
            with open(os.path.join(settings.BASE_DIR, 'files', 'Webhook.txt'),
                      'r') as file:
                body = file.read()
            response1 = self.create_apex_class('Webhook', body)
            if response1.status_code != 201:
                response = response1.json()
                # Si el APEX Class ya existe (es duplicado), continuamos, si es otro error, paramos
                if 'errorCode' in response[0] and response[0][
                    'errorCode'] == 'DUPLICATE_VALUE':
                    pass
                else:
                    return False

            response2 = self.create_remote_site(
                'GearPlug' + 'RemoteSiteSetting{}'.format(webhook.id), url)
            if response2.status_code != 200:
                return False

            with open(os.path.join(settings.BASE_DIR, 'files',
                                   'WebhookTrigger.txt'), 'r') as file:
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
                webhook.save(
                    update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True
        return False

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() in ['sobject']:
            tup = tuple({'id': p, 'name': p} for p in self.get_sobject_list())
            return tup
        if action_specification.name.lower() in ['event']:
            tup = tuple({'id': p, 'name': p} for p in self.get_event_list())
            return tup
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

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
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'order by':
            return tuple({'id': c['name'], 'name': c['name']} for c in
                         self.describe_table())
        elif action_specification.name.lower() == 'unique':
            return tuple({'id': c['name'], 'name': c['name']} for c in
                         self.describe_table())
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

    def has_webhook(self):
        return True


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

    def download_to_stored_data(self, connection_object, plug, ):
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
    _base_url = None
    _access_key = None
    _session_name = None
    _token = None
    _user_id = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(VtigerController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(VtigerController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._user = self._connection_object.connection_user
                self._password = self._connection_object.connection_password
                self._base_url = self._connection_object.url
                self._access_key = self._connection_object.connection_access_key
            except Exception as e:
                print(e)

        if self._base_url is not None and self._access_key is not None:
            if not self._token:
                self._token = self.get_token(self._user, self._base_url)
            self._session_name, self._user_id = self.login()
            if self._session_name is None:
                self._token = self.get_token(self._user, self._base_url)
                self._session_name, self._user_id = self.login()
        else:
            return None

    def test_connection(self):
        return self._session_name is not None

    def get_token(self, user, base_url):
        endpoint_url = '/webservice.php?operation=getchallenge'
        url = base_url + endpoint_url
        if url is not None:
            try:
                values = {'operation': 'getchallenge', 'username': user}
                r = requests.get(url, params=values)
                if r.status_code == 200:
                    r = r.json()
                    return r['result']['token']
                return None
            except Exception as e:
                return None

    def get_tokenized_access_key(self):
        try:
            return md5(
                str(self._token + self._access_key).encode('utf-8')).hexdigest()
        except Exception as es:
            return None

    def login(self):
        endpoint_url = '/webservice.php'
        url = self._base_url + endpoint_url
        tokenized_access_key = self.get_tokenized_access_key()
        values = {'accessKey': tokenized_access_key, 'operation': 'login',
                  'username': self._user}
        data = urllib.parse.urlencode(values).encode('utf-8')
        try:
            request = urllib.request.Request(url, data)
            response = urllib.request.urlopen(request).read().decode('utf-8')
        except Exception as e:
            print(e)
        try:
            response = json.loads(response)
        except Exception as e:
            print(e)

        if response['success'] is True:
            self._session_name = response['result']['sessionName']
            self._user_id = response['result']['userId']
            return self._session_name, self._user_id
        elif response['success'] is not True:
            return None, None

    def get_module(self, module_name):
        endpoint_url = '/webservice.php'
        url = self._base_url + endpoint_url
        values = {'sessionName': self._session_name, 'operation': 'describe',
                  'elementType': module_name}
        r = requests.get(url, params=values)
        if r.status_code == 200:
            r = r.json()
            return {'name': module_name, 'id': r['result']['idPrefix']}
        raise Exception("Error retrieving module data.")

    def get_modules(self):
        endpoint_url = '/webservice.php'
        url = self._base_url + endpoint_url
        try:
            values = {
                'sessionName': self._session_name,
                'operation': 'listtypes'
            }
            r = requests.get(url, params=values)
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

    def get_module_elements(self, module=None, gt=None, limit=30):
        endpoint_url = '/webservice.php'
        url = self._base_url + endpoint_url
        query = "SELECT * FROM {0} ".format(module)
        if gt is not None:
            query += "createdtime > {}".format(gt)
        query += " ORDER BY createdtime desc;"
        values = {'sessionName': self._session_name, 'operation': 'query',
                  'query': query}
        r = requests.get(url, params=values).json()
        try:
            data = r['result']
            return data
        except Exception as e:
            print(e)
            return []

    def create_register(self, module, **kwargs):

        endpoint_url = '/webservice.php'
        url = self._base_url + endpoint_url

        kwargs['assigned_user_id'] = self._user_id
        for k, v in kwargs.items():
            try:
                kwargs[k] = (self.get_module(v)["id"])
            except Exception as e:
                print(e)
                continue

        kwargs['elementType'] = module
        parameters = {
            'operation': 'create',
            'sessionName': self._session_name,
            'elementType': kwargs['elementType'],
            'element': json.dumps(kwargs)
        }
        try:
            parameters = urllib.parse.urlencode(parameters)
            connection = urllib.request.urlopen(url,
                                                parameters.encode('utf-8'))
            response = connection.read().decode('utf-8')
            response = json.loads(response)
        except Exception as e:
            print(e)

        if response['success'] is True:
            return response
        else:
            return False

    def get_module_name(self, module_id):
        try:
            for module in self.get_modules():
                if module['id'] == module_id:
                    return module['name']
        except Exception as e:
            print(e)

    def get_module_fields(self, module_name):
        endpoint_url = '/webservice.php'
        url = self._base_url + endpoint_url

        try:
            details = {
                'operation': 'describe',
                'sessionName': self._session_name,
                'elementType': str(module_name)
            }
            response = requests.get(url, params=details).json()
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

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, limit=50, **kwargs):
        module_id = self._plug.plug_action_specification.get(
            action_specification__name__iexact='module').value
        data = self.get_module_elements(limit=30, module=self.get_module_name(module_id), gt=last_source_record)
        new_data = []
        for product in data:
            unique_value = product['id']
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=unique_value)
            if not q.exists():
                new_item = [StoredData(name=key, value=value or '', object_id=unique_value,
                                       connection=connection_object.connection, plug=plug) for key, value in
                            product.items()]
            new_data.append(new_item)
        obj_last_source_record = None
        result_list = []
        if new_data:
            data.reverse()
            new_data.reverse()
            for item in new_data:
                obj_id = item[0].object_id
                obj_raw = "RAW DATA NOT FOUND."
                for i in data:
                    if obj_id in i.values():
                        obj_raw = i
                        break
                data.remove(i)

                is_stored, object_id = self._save_row(item)
                if object_id != obj_id:
                    print("ERROR NO ES EL MISMO ID:  {0} != 1}".format(object_id, obj_id))
                    # TODO: CHECK RAISE
                result_list.append(
                    {'identifier': {'name': 'id', 'value': object_id}, 'raw': obj_raw, 'is_stored': is_stored})
            for item in result_list:
                for k, v in item['raw'].items():
                    if k == 'createdtime':
                        obj_last_source_record = v
                        (obj_last_source_record)
                        break
            return {'downloaded_data': result_list, 'last_source_record': obj_last_source_record}
        return False

    def _save_row(self, item):
        try:
            for stored_data in item:
                stored_data.save()
            return True, stored_data.object_id
        except Exception as e:
            return False, item[0].object_id

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Vtiger) for f in fields]

    def get_target_fields(self, **kwargs):
        module_id = self._plug.plug_action_specification.get(
            action_specification__name__iexact='module').value
        try:
            module_fields = (
                self.get_module_fields(self.get_module_name(module_id)))
        except Exception as e:
            print(e)
        fields_list = []
        for i in module_fields:
            if i['editable'] is True:
                fields_list.append(i)
        if len(fields_list) > 0:
            return fields_list
        else:
            return False

    def send_stored_data(self, data_list):
        obj_list = []
        module_id = self._plug.plug_action_specification.get(action_specification__name__iexact='module').value
        module_name = self.get_module_name(module_id)
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                task = self.create_register(module_name, **item)
            except Exception as e:
                raise
            try:
                if task['success'] is True:
                    obj_result['response'] = "Succesfully created item with id {0}.".format(task['result']['id'])
                    obj_result['sent'] = True
                    obj_result['identifier'] = task['result']['id']
                else:
                    obj_result['response'] = "Failed to created item."
                    obj_result['sent'] = False
                    obj_result['identifier'] = "Failed to created item."
                obj_list.append(obj_result)
            except Exception as e:
                print(e)
        return obj_list


class ActiveCampaignController(BaseController):
    _host = None
    _key = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(ActiveCampaignController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(ActiveCampaignController, self).create_connection(connection=connection, plug=plug)
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

    def get_custom_fields(self):
        params = [('api_action', "list_field_view"), ('api_key', self._key), ('api_output', 'json'), ('ids', 'all')]
        url = "{0}/admin/api.php".format(self._host)
        r = requests.get(url=url, params=params)
        if r.status_code == 200:
            result = r.json()
            return {str(int(v['id']) - 1): {'name': v['perstag'], 'id': v['id'], 'label': v['title']} for (k, v) in
                    result.items() if k not in ['result_code', 'result_output', 'result_message']}
        return []

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
            if action_specification.name.lower() == 'list':
                for i in self.get_lists():
                    return tuple({'id': i['id'], 'name': i['name']} for i in
                                 self.get_lists())
            else:
                raise ControllerError("That specification doesn't belong "
                                      "to an action in this connector.")
        except Exception as e:
            print(e)

    def test_connection(self):
        try:
            return self.get_account_info() is True
        except:
            return False

    def create_webhook(self):
        action_name = self._plug.action.name
        action = 'subscribe'
        if action_name == 'new subscriber' or 'new unsubscriber':
            selected_list = self._plug.plug_action_specification.get(
                action_specification__name='list')
            list_id = selected_list.value
            if action_name == 'new unsubscriber':
                action = 'unsubscribe'
        elif action_name == 'new contact':
            list_id = 0
        # Creacion de Webhook
        webhook = Webhook.objects.create(name='activecampaign', url='',
                                         plug=self._plug, expiration='')

        # Verificar ngrok para determinar url_base
        url_base = settings.WEBHOOK_HOST
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
            "lists": list_id,
            "action": action,
            "init": "admin"
        }
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, data=post_array, params=params)
        if r.status_code == 200 or r.status_code == 201:

            webhook.url = url_base + url_path
            webhook.generated_id = r.json()['id']
            webhook.is_active = True
            webhook.save(
                update_fields=['url', 'generated_id', 'is_active'])
            return True
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            return False

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [
            MapField(f, controller=ConnectorEnum.ActiveCampaign) for f in
            fields
        ]

    def get_target_fields(self, **kwargs):
        action = self._plug.action.name
        if action == 'unsubscribe a contact':
            return [{'name': 'email', 'label': 'Email', 'type': 'varchar', 'required': True}]
        return [
            {'name': 'email', 'label': 'Email', 'type': 'varchar', 'required': True},
            {'name': 'first_name', 'label': 'First Name', 'type': 'varchar', 'required': False},
            {'name': 'last_name', 'label': 'Last Name', 'type': 'varchar', 'required': False},
            {'name': 'phone', 'label': 'Phone', 'type': 'varchar', 'required': False},
            {'name': 'orgname', 'label': 'Organization Name', 'type': 'varchar', 'required': False},
        ]

    def create_contact(self, data):
        params = [
            ('api_action', "contact_sync"),
            ('api_key', self._key),
            ('api_output', 'json'),
        ]
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, data=data, params=params).json()
        return r

    def subscribe_contact(self, data):
        _list_id = self._plug.plug_action_specification.get(action_specification__name='list').value
        params = [
            ('api_action', "contact_add"),
            ('api_key', self._key),
            ('api_output', 'json'),
        ]
        data['p[{0}]'.format(_list_id)] = _list_id
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, data=data, params=params).json()
        return r

    def unsubscribe_contact(self, email):
        _list_id = self._plug.plug_action_specification.get(action_specification__name='list').value
        data = self.contact_view_email(email['email'])
        params = [
            ('api_action', "contact_edit"),
            ('api_key', self._key),
            ('api_output', 'json'),
        ]
        data['p[{0}]'.format(_list_id)] = _list_id
        data['status[{0}]'.format(_list_id)] = 2
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, data=data, params=params).json()
        r['subscriber_id'] = data['id']
        return r

    def contact_view_email(self, email):
        params = [
            ('api_action', "contact_view_email"),
            ('api_key', self._key),
            ('api_output', 'json'),
            ('email', email),
        ]
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, params=params).json()
        return r

    def send_stored_data(self, data_list):
        extra = {'controller': 'activecampaign'}
        action = self._plug.action.name
        result_list = []
        for item in data_list:
            sent = False
            identifier = ""
            if action == 'create contact':
                response = self.create_contact(item)
            elif action == 'subscribe a contact':
                response = self.subscribe_contact(item)
            elif action == 'unsubscribe a contact':
                response = self.unsubscribe_contact(item)
            if response['result_code'] == 1:
                sent = True
                identifier = response['subscriber_id']
                self._log.info(
                    'Item: %s successfully sent.' % (response['subscriber_id']),
                    extra=extra)
            else:
                print(response['result_message'])
                extra['status'] = 'f'
                self._log.info(
                    'Item: %s failed to send.' % (
                        list(item.items())[0][1]),
                    extra=extra)
            result_list.append(
                {'data': dict(item), 'response': response['result_message'], 'sent': sent, 'identifier': identifier})
        return result_list

    def download_to_stored_data(self, connection_object=None, plug=None, last_source_record=None, data=None, **kwargs):
        new_data = []
        if data is not None:
            contact_id = data['id']
            object_id = int(contact_id)
            q = StoredData.objects.filter(object_id=object_id, connection=connection_object.id, plug=plug.id)
            if not q.exists():
                for k, v in data.items():
                    new_data.append(
                        StoredData(name=k, value=v or '', object_id=object_id, connection=connection_object.connection,
                                   plug=plug))
            if new_data:
                field_count = len(data)
                extra = {'controller': 'activecampaign'}
                is_stored = False
                for i, item in enumerate(new_data):
                    try:
                        item.save()
                        is_stored = True
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
                result_list = [{'raw': data, 'is_stored': is_stored, 'identifier': {'name': 'id', 'value': object_id}}]
            return {'downloaded_data': result_list, 'last_source_record': object_id}
        return False

    def contact_view(self, id):
        params = [
            ('api_action', "contact_view"),
            ('api_key', self._key),
            ('api_output', 'json'),
            ('id', id),
        ]
        url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=url, params=params)
        return r.json()

    def delete_webhooks(self, id):
        params = [
            ('api_action', "webhook_delete"),
            ('api_key', self._key),
            ('api_output', 'json'),
            ('id', id),
        ]
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, params=params)
        return r.json()

    def delete_contact(self, id):
        params = [
            ('api_action', "contact_delete"),
            ('api_key', self._key),
            ('api_output', 'json'),
            ('id', id),
        ]
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, params=params)
        return r.json()

    def list_webhooks(self, id):
        params = [
            ('api_action', "webhook_view"),
            ('api_key', self._key),
            ('api_output', 'json'),
            ('id', id),
        ]
        final_url = "{0}/admin/api.php".format(self._host)
        r = requests.post(url=final_url, params=params)
        return r.json()

    def do_webhook_process(self, body=None, POST=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
        action_name = webhook.plug.action.name
        if 'list' in POST and POST['list'] == '0' and action_name != 'new contact':
            # ActiveCampaign envia dos webhooks, el primero es cuando se crea el contacto, el segundo cuando el contacto
            # creado es agregado a una lista. Cuando el contacto es agregado a una lista el webhook incluye los custom
            # fields por eso descartamos los webhooks de contactos que no hayan sido agregados a una lista (list = 0).
            return HttpResponse(status=200)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            expr = '\[(\w+)\](?:\[(\d+)\])?'
            clean_data = {}
            custom_fields = self.get_custom_fields()
            for k, v in POST.items():
                m = re.search(expr, k)
                if m:
                    n = m.group(2)
                    if n is None:
                        key = m.group(1)
                    else:
                        key = custom_fields[str(int(n) - 1)]['label']
                else:
                    key = None
                if key is not None and key not in clean_data:
                    clean_data[key] = v
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
            if self.test_connection():
                self.download_source_data(data=clean_data)
                webhook.plug.save()
        return HttpResponse(status=200)

    def has_webhook(self):
        return True


class InfusionSoftController(BaseController):
    _token = None
    _refresh_token = None
    _token_expiration_time = None
    _actual_time = time.time()

    def __init__(self, *args, **kwargs):
        super(InfusionSoftController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(InfusionSoftController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._refresh_token = self._connection_object.refresh_token
                    self._token_expiration_time = self._connection_object.token_expiration_time
                except Exception as e:
                    print(e)

    def test_connection(self):
        if self.is_token_expired():
            self.refresh_token()
        information = ''
        return information is not None

    def is_token_expired(self):
        try:
            return float(self._token_expiration_time) > self._actual_time
        except Exception as e:
            print(e)
            return False

    def refresh_token(self):
        string_to_encode = (str(settings.INFUSIONSOFT_CLIENT_ID + ':' + settings.INFUSIONSOFT_CLIENT_SECRET)).encode(
            'utf-8')
        encoded = base64.b64encode(string_to_encode)
        auth_string = 'basic' + str(encoded)
        headers = {
            "Accept": "application/json, */*",
            "Authorization": "{0}".format(auth_string)
        }
        data = {
            "grant_type": 'refresh_token',
            "refresh_token": self._refresh_token,
        }
        try:
            response = requests.post(
                'https://api.infusionsoft.com/token',
                headers=headers,
                json=data
            )

            self._token = response.json()['access_token']
            self._refresh_token = response.json()['refresh_token']
            self._token_expiration_time = response.json()['expires_at']

        except Exception as e:
            print(e)
            return False

    def get_contact(self, id):
        if self.is_token_expired() == True:
            self._refresh_token
        headers = {
            "Accept": "application/json, */*",
            "Authorization": "Bearer {0}".format(self._token)
        }
        try:
            response = requests.get('https://api.infusionsoft.com/crm/rest/v1/contacts/{0}'.format(str(id)),
                                    headers=headers)
            return response.json()
        except Exception as e:
            print(e)
            return False

    def create_update_contact(self, **kwargs):
        if self.is_token_expired() == True:
            self._refresh_token
        headers = {
            "Accept": "application/json, */*",
            "Authorization": "Bearer {0}".format(self._token)
        }
        data = {"addresses": [
            {
                "field": "BILLING",
                "line1": kwargs['addresses'],
            }
        ],
            "email_addresses": [
                {
                    "email": kwargs['email_addresses'],
                    "field": "EMAIL1"
                }
            ],
            "phone_numbers": [
                {
                    "field": "PHONE1",
                    "number": kwargs['phone_numbers'],
                }
            ],
            "family_name": kwargs['family_name'],
            "given_name": kwargs['given_name'],
            "duplicate_option": "Email",
        }
        try:
            response = requests.put(
                "https://api.infusionsoft.com/crm/rest/v1/contacts",
                headers=headers,
                json=data
            )
            return response
        except Exception as e:
            print(e)
            return False

    def create_webhook(self):
        if self.is_token_expired() == True:
            self._refresh_token
        action = self._plug.action.name
        if action == 'Detect actions in Contacts':
            option = self._plug.plug_action_specification.get(
                action_specification__name='contact action')

            # Creacion de Webhook
            webhook = Webhook.objects.create(name='infusionsoft', plug=self._plug, url='', is_active=False, )

            # Verificar ngrok para determinar url_base
            url_base = settings.WEBHOOK_HOST
            url_path = reverse('home:webhook', kwargs={'connector': 'infusionsoft', 'webhook_id': webhook.id})
            hookUrl = url_base + url_path
            headers = {
                "Accept": "application/json, */*",
                'Authorization': 'Bearer {}'.format(self._token)
            }
            data = {
                "eventKey": str(option.value),
                "hookUrl": str(hookUrl)
            }
            response = requests.post("https://api.infusionsoft.com/crm/rest/v1/hooks",
                                     headers=headers, json=data)

            try:
                r = response.json()
            except Exception as e:
                r = {'status': 'Unverified'}
                print(e)
            if response.status_code in [201, 200] and r['status'].lower() == 'verified':
                webhook.url = url_base + url_path
                webhook.generated_id = response.json()['key']
                webhook.is_active = True
                webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True

        elif action == 'Detect actions in Opportunities':
            option = self._plug.plug_action_specification.get(
                action_specification__name='opportunity action')

            # Creacion de Webhook
            webhook = Webhook.objects.create(name='infusionsoft',
                                             plug=self._plug, url='')

            # Verificar ngrok para determinar url_base
            url_base = settings.WEBHOOK_HOST
            url_path = reverse('home:webhook',
                               kwargs={'connector': 'infusionsoft',
                                       'webhook_id': webhook.id})
            hookUrl = url_base + url_path
            headers = {
                "Accept": "application/json, */*",
                'Authorization': 'Bearer {}'.format(self._token)
            }
            data = {
                "eventKey": str(option.value),
                "hookUrl": str(hookUrl)
            }
            response = requests.post(
                "https://api.infusionsoft.com/crm/rest/v1/hooks",
                headers=headers, json=data)
            try:
                r = response.json()
            except Exception as e:
                r = {'status': 'Unverified'}
                print(e)
            if response.status_code in [201, 200] and r['status'].lower() == 'verified':
                webhook.url = url_base + url_path
                webhook.generated_id = response.json()['key']
                webhook.is_active = True
                webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True

        return False

    def do_webhook_process(self, body=None, GET=None, POST=None, META=None, webhook_id=None, **kwargs):
        response = HttpResponse(status=400)
        if POST is not None:
            if 'HTTP_X_HOOK_SECRET' in META:
                response.status_code = 200
                response['X-Hook-Secret'] = META['HTTP_X_HOOK_SECRET']
                return response

            if body['object_keys'][0]['id'] is not None:
                object_id = body['object_keys'][0]['id']
                event_key = body['event_key']
                try:
                    plug = Plug.objects.get(Q(gear_source__is_active=True) | Q(is_tested=False),
                                            plug_type__iexact='source',
                                            connection__connector__name__iexact='infusionsoft',
                                            plug_action_specification__value__iexact=event_key,
                                            webhook__id=webhook_id, )
                except Exception as e:
                    print(e)
                    plug = None
                if plug:
                    self.create_connection(plug.connection.related_connection, plug)
                    if self.test_connection():
                        try:
                            contact = self.get_contact(object_id)
                        except Exception as e:
                            print(e)
                        self.download_source_data(contact=contact)
        return response

    def hooks_types(self):
        if self.is_token_expired() == True:
            self._refresh_token

        headers = {
            "Accept": "application/json, */*",
            "Authorization": "Bearer {0}".format(self._token)
        }
        response = requests.get(
            "https://api.infusionsoft.com/crm/rest/v1/hooks/event_keys",
            headers=headers)
        event_keys = response.json()
        return event_keys

    def get_action_specification_options(self, action_specification_id):
        if self.is_token_expired() == True:
            self._refresh_token
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'contact action':
            options = []
            opt = self.hooks_types()
            for i in opt:
                if 'contact' in i:
                    options.append(i)
            return tuple(
                {'id': k, 'name': k.replace('.', ' ')} for k in options
            )
        elif action_specification.name.lower() == 'opportunity action':
            options = []
            opt = self.hooks_types()
            for i in opt:
                if 'opportunity' in i:
                    options.append(i)
            return tuple(
                {'id': k, 'name': k.replace('.', ' ')} for k in options
            )
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

    def download_to_stored_data(self, connection_object=None, plug=None,
                                contact=None, **kwargs):
        if self.is_token_expired() == True:
            self._refresh_token
        if contact is not None:
            contact_id = contact['id']
            q = StoredData.objects.filter(
                connection=connection_object.connection, plug=plug,
                object_id=contact_id)
            contact_data = []

            flat_contacts = {}

            for k, v in contact.items():
                if type(v) == dict:
                    for x, z in v.items():
                        flat_contacts['{0}_{1}'.format(k, x)] = z
                else:
                    flat_contacts[k] = v

            if not q.exists():
                for k, v in flat_contacts.items():
                    contact_data.append(
                        StoredData(connection=connection_object.connection, plug=plug, object_id=contact_id, name=k,
                                   value=v or ''))
            extra = {}
            for data in contact_data:
                try:
                    extra['status'] = 's'
                    extra = {'controller': 'infusionSoft'}
                    data.save()
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            data.object_id, data.plug.id,
                            data.connection.id),
                        extra=extra)
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s failed.' % (
                            data.object_id, data.plug.id,
                            data.connection.id),
                        extra=extra)
            return True
        return False

    def get_target_fields(self, **kwargs):
        return [{'name': 'given_name', 'type': 'text', 'required': False},
                {'name': 'family_name', 'type': 'text', 'required': False},
                {'name': 'middle_name', 'type': 'text', 'required': False},
                {'name': 'id', 'type': 'text', 'required': False},
                {'name': 'date_created', 'type': 'text', 'required': False},
                {'name': 'phone_numbers', 'type': 'text', 'required': True},
                {'name': 'addresses', 'type': 'text', 'required': False},
                {'name': 'email_addresses', 'type': 'text', 'required': True},
                {'name': 'company_company_name', 'type': 'text', 'required': False},
                {'name': 'company_id', 'type': 'text', 'required': False}]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.InfusionSoft) for f in fields]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'InfusionSoft'}
            for item in data_list:
                task = self.create_update_contact(**item)
                if task.status_code in [200, 201]:
                    extra['status'] = 's'
                    print(task.json())
                    self._log.info('Item: %s successfully sent.' % (
                        task.json()['given_name']), extra=extra)
                    obj_list.append(task)
                else:
                    extra['status'] = 'f'
                    self._log.info('Item: failed to send.', extra=extra)
            return obj_list
        raise ControllerError("There's no plug")


class OdooCRMController(BaseController):
    _user = None
    _password = None
    _url = None
    _database = None
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(OdooCRMController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(OdooCRMController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._user = self._connection_object.connection_user
                self._password = self._connection_object.connection_password
                self._url = self._connection_object.url
                self._database = self._connection_object.database
            except AttributeError as e:
                raise ControllerError(code=1, controller=ConnectorEnum.OdooCRM,
                                      message='Error getting the OdooCRM attributes args. {}'.format(str(e)))
        else:
            raise ControllerError('No connection.')
        if self._url is not None and self._database is not None and self._user is not None and self._password is not None:
            try:
                self._client = OdooCRMClient(self._url, self._database, self._user, self._password)
            except requests.exceptions.MissingSchema:
                raise
            except InvalidLogin as e:
                raise ControllerError(code=2, controller=ConnectorEnum.OdooCRM,
                                      message='Invalid login. {}'.format(str(e)))

    def test_connection(self):
        return self._client is not None

    def get_search_partner(self, query, params):
        try:
            return self._client.search_partner(query, params)
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.OdooCRM, message='Error. {}'.format(str(e)))

    def get_read_partner(self, query):
        try:
            return self._client.read_partner(query)
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.OdooCRM, message='Error. {}'.format(str(e)))

    def get_list_fields(self):
        try:
            fields = self._client.list_fields_partner()
            _list = []
            for k, v in fields.items():
                v['name'] = k
                _list.append(v)
            return _list
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.OdooCRM, message='Error. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, limit=50, last_source_record=None, **kwargs):

        """
            NOTE: Se ordena por el campo: 'date_entered'.
        :param connection_object:
        :param plug:
        :param limit:
        :param last_source_record:
        :param kwargs:
        :return:
        """
        query = [[]]
        if last_source_record is not None:
            query = [[['create_date', '>', last_source_record]]]
        entries_id = self.get_search_partner(query, {'limit': limit, 'order': 'id desc'})
        if not entries_id:
            return False
        entries = self.get_read_partner([entries_id])
        raw_data = []
        new_data = []
        for item in entries:
            try:
                del item['image']
            except KeyError:
                pass
            try:
                del item['image_small']
            except KeyError:
                pass
            try:
                del item['image_medium']
            except KeyError:
                pass
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                item_data = []
                obj_raw = item
                for k, v in obj_raw.items():
                    if isinstance(v, str) and v.isspace():
                        obj_raw[k] = ''
                for k, v in obj_raw.items():
                    item_data.append(
                        StoredData(name=k, value=v or '', object_id=item['id'], connection=connection_object.connection,
                                   plug=plug))
                raw_data.append(obj_raw)
                new_data.append(item_data)
        if new_data:
            result_list = []
            for item in new_data:
                for stored_data in item:
                    try:
                        stored_data.save()
                    except Exception as e:
                        is_stored = False
                        break
                    is_stored = True
                obj_raw = "RAW DATA NOT FOUND."
                for obj in raw_data:
                    if stored_data.object_id == obj['id']:
                        obj_raw = obj
                        break
                raw_data.remove(obj_raw)
                result_list.append(
                    {'identifier': {'name': 'id', 'value': stored_data.object_id}, 'is_stored': is_stored,
                     'raw': obj_raw, })
            return {'downloaded_data': result_list, 'last_source_record': result_list[0]['raw']['create_date']}
        return False

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                res = self.set_entry([dict(item)])
                obj_result['response'] = res
                obj_result['sent'] = True
                obj_result['identifier'] = res
            except Exception as e:
                obj_result['response'] = str(e)
                obj_result['sent'] = False
                obj_result['identifier'] = '-1'
            obj_list.append(obj_result)
        return obj_list

    def set_entry(self, item):
        try:
            return self._client.create_partner(item)
        except WrongParameter as e:
            raise ControllerError(code=4, controller=ConnectorEnum.OdooCRM,
                                  message='Wrong Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.SugarCRM, message='Error. {}'.format(str(e)))

    def get_mapping_fields(self, **kwargs):
        fields = self.get_list_fields()
        return [MapField(f, controller=ConnectorEnum.OdooCRM) for f in fields]

    def get_action_specification_options(self, action_specification_id):
        pass
        #     action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        #     if action_specification.name.lower() == 'module':
        #         return tuple({'id': m['module_key'], 'name': m['module_label']}
        #                      for m in self.get_available_modules()['modules'] if m['module_key'] != 'Home')
        #     else:
        #         raise ControllerError("That specification doesn't belong to an action in this connector.")
