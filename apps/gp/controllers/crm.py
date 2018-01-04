from hashlib import md5
from urllib.parse import urlparse
from dateutil.parser import parse
from django.core.urlresolvers import reverse
from django.db.models import Q
from salesforce.client import Client as SalesforceClient
from salesforce.exceptions import BadOAuthTokenError
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
from batchbook.client import Client as ClientBatchbook
from actcrm.client import Client as ActCRMClient
from agilecrm.client import Client as AgileCRMClient
from activecampaign.client import Client as ActiveCampaignClient
from hubspot.client import Client as HubSpotClient
import datetime
import time
import requests
import json
import os
import string
import base64
import urllib.error
import urllib.request
import xmldict


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
            except Exception as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.SugarCRM,
                                      message='The attributes necessary to make the connection were not obtained.. {}'.format(str(e)))
        else:
            raise ControllerError(code=1002, controller=ConnectorEnum.SugarCRM,
                                  message='The controller is not instantiated correctly.')
        try:
            session = requests.Session()
            self._client = SugarClient(self._url, self._user, self._password, session=session)
        except requests.exceptions.MissingSchema:
            raise ControllerError(code=1003, controller=ConnectorEnum.SugarCRM,
                                  message='Missing Schema.')
        except InvalidLogin as e:
            raise ControllerError(code=1003, controller=ConnectorEnum.SugarCRM,
                                  message='Invalid login. {}'.format(str(e)))
        except Exception as e:
            raise ControllerError(code=1003, controller=ConnectorEnum.SugarCRM,
                                  message='Error in the instantiation of the client.. {}'.format(str(e)))
        try:
            self._module = self._plug.plug_action_specification.get(
                action_specification__name__iexact='module').value
        except Exception as e:
            raise ControllerError(code=1005, controller=ConnectorEnum.SugarCRM,
                                  message='Error while choosing specifications. {}'.format(str(e)))

    def test_connection(self):
        """
        Debido a un mejor metodo para verificar la conexion se utiliza el metodo
        get_available_modules()
        :return:
        """
        try:
            response = self.get_available_modules()
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.SugarCRM,
            #                       message='Error in the connection test.. {}'.format(str(e)))
            return False
        if response is not None and isinstance(response, dict) and 'modules' in response:
            return True
        else:
            return False

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
        new_data = []
        for item in entries:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                item_data = []
                for k, v in item['name_value_list'].items():
                    item_data.append(StoredData(name=k, value=v['value'] or '', object_id=item['id'],
                                                connection=connection_object.connection, plug=plug))
                new_data.append(item_data)
        downloaded_data = []
        for new_item in new_data:
            history_obj = {'identifier': None, 'is_stored': True, 'raw': {}}
            StoredData.objects.bulk_create(new_item)
            for field in new_item:
                history_obj['raw'][field.name] = field.value
            history_obj['identifier'] = {'name': 'id', 'value': field.object_id}
            downloaded_data.append(history_obj)
        if downloaded_data:
            return {'downloaded_data': downloaded_data, 'last_source_record': downloaded_data[0]['raw'][
                'date_entered']}
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
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
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
    """
    Updated by Miguel on Dec 12 2017

    """
    token = None
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        BaseController.__init__(self, connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(SalesforceController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self.token = json.loads(self._connection_object.token)
            except AttributeError as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.Salesforce.name,
                                      message='The attributes necessary to make the connection were not obtained {}'.format(
                                          str(e)))
        else:
            raise ControllerError(code=1002, controller=ConnectorEnum.Salesforce.name,
                                  message='The controller is not instantiated correctly.')
        try:
            self._client = SalesforceClient(settings.SALESFORCE_CLIENT_ID, settings.SALESFORCE_CLIENT_SECRET,
                                            settings.SALESFORCE_INSTANCE_URL, settings.SALESFORCE_VERSION)
            self._client.set_access_token(self.token)
        except Exception as e:
            raise ControllerError(code=1003, controller=ConnectorEnum.Salesforce.name,
                                  message='Error in the instantiation of the client.. {}'.format(str(e)))

    def test_connection(self):
        try:
            user_info = self._client.get_user_info()
        except BadOAuthTokenError as e:
            new_token = self._client.refresh_token()
            # Actualiza el token del controlador con el nuevo token obtenido y posteriormente guarda en BD.
            self.token.update(new_token)
            self._client.set_access_token(self.token)
            self._connection_object.token = json.dumps(self.token)
            self._connection_object.save()
            #TODO: Intentar obtener la info nuevamente
            return False
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.Salesforce.name,
            # message='Error in the connection test... {}'.format(str(e)))
            return False
        if user_info and isinstance(user_info, dict) and 'user_id' in user_info:
            return True
        return False

    def send_stored_data(self, data_list, is_first=False):
        result_list = []
        if is_first and data_list:
            try:
                data_list = [data_list[-1]]
            except Exception as e:
                data_list = []
        if self._plug is not None:
            for obj in data_list:
                try:
                    _result = self.create(obj)
                    identifier = _result['id']
                    _sent = True
                except Exception as e:
                    _result = str(e)
                    identifier = '-1'
                    _sent = False
                result_list.append({'data': dict(obj), 'response': _result, 'sent': _sent, 'identifier': identifier})
        return result_list

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, event=None, **kwargs):
        if event is None:
            return False
        new_data = []
        event_id = event['new'][0]['Id']
        new = event.pop('new')
        event.update(new[0])
        q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=event_id)
        if not q.exists():
            for k, v in event.items():
                obj = StoredData(connection=connection_object.connection, plug=plug, object_id=event_id, name=k,
                                 value=v or '')
                new_data.append(obj)
        is_stored = False
        for item in new_data:
            try:
                item.save()
                is_stored = True
            except Exception as e:
                print(e)
        result_list = [{'raw': event, 'is_stored': is_stored, 'identifier': {'name': 'id', 'value': event_id}}]
        return {'downloaded_data': result_list, 'last_source_record': event_id}

    def create(self, fields):
        birthdate = fields.pop('Birthdate', None)
        if birthdate:
            fields['Birthdate'] = parse(birthdate).strftime('%Y-%m-%d')
        email_bounced_date = fields.pop('EmailBouncedDate', None)
        if email_bounced_date:
            fields['EmailBouncedDate'] = parse(email_bounced_date).strftime('%Y-%m-%dT%H:%M:%S%z')
        last_activity_date = fields.pop('LastActivityDate', None)
        if last_activity_date:
            fields['LastActivityDate'] = parse(last_activity_date).strftime('%Y-%m-%d')
        last_referenced_date = fields.pop('LastReferencedDate', None)
        if last_referenced_date:
            fields['LastReferencedDate'] = parse(last_referenced_date).strftime('%Y-%m-%d')
        last_viewed_date = fields.pop('LastViewedDate', None)
        if last_viewed_date:
            fields['LastViewedDate'] = parse(last_viewed_date).strftime('%Y-%m-%d')
        converted_date = fields.pop('ConvertedDate', None)
        if converted_date:
            fields['ConvertedDate'] = parse(converted_date).strftime('%Y-%m-%d')

        for k, v in fields.items():
            if v.lower() == 'true':
                fields[k] = True
            elif v.lower() == 'false':
                fields[k] = False

        if self._plug.action.name == 'create contact':
            r = self._client.create_sobject('Contact', data=dict(fields))
        else:
            r = self._client.create_sobject('Lead', data=dict(fields))
        return r

    def get_contact_meta(self):
        data = self._client.get_sobject_describe('Contact')
        return [f for f in data['fields'] if f['createable'] and f['type'] != 'reference']

    def get_lead_meta(self):
        data = self._client.get_sobject_describe('Lead')
        return [f for f in data['fields'] if f['createable'] and f['type'] != 'reference']

    def get_mapping_fields(self):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Salesforce) for f in fields]

    def get_target_fields(self, **kwargs):
        if self._plug.action.name == 'create contact':
            return self.get_contact_meta()
        else:
            return self.get_lead_meta()

    def get_sobjects(self):
        return self._client.get_describe_global()

    def cget_sobject(self):
        _dict = self.get_sobjects()
        return [o['name'] for o in _dict['sobjects'] if o['triggerable']]

    def create_webhook(self):
        sobject = self._plug.plug_action_specification.get(action_specification__name='sobject')
        event = self._plug.plug_action_specification.get(action_specification__name='event')
        # Creacion de Webhook
        webhook = Webhook.objects.create(name='salesforce', plug=self._plug, url='', expiration='')
        # Verificar host para determinar url_base
        url_base = settings.WEBHOOK_HOST
        url_path = reverse('home:webhook', kwargs={'connector': 'salesforce', 'webhook_id': webhook.id})
        url = url_base + url_path
        with open(os.path.join(settings.BASE_DIR, 'apps', 'gp', 'files', 'salesforce', 'webhook.txt'), 'r') as file:
            body = file.read()

        apex_class_response = self._client.create_apex_class('GearPlug Webhook', body)
        # Si APEX Class ya existe (probablemente duplicado de GearPlug), entonces continuamos, si es otro error, paramos
        if 'errorCode' in apex_class_response and apex_class_response['errorCode'] != 'DUPLICATE_VALUE':
            return False

        remote_site_response = self._client.create_remote_site('GearPlugRemoteSiteSetting{}'.format(webhook.id), url)
        _dict = xmldict.xml_to_dict(remote_site_response)
        # TODO: Comprobar que _dict success es True, de lo contrario lanzar excepción (?)

        with open(os.path.join(settings.BASE_DIR, 'apps', 'gp', 'files', 'salesforce', 'webhook_trigger.txt'),
                  'r') as file:
            body = file.read()

        body = body.replace('{name}', 'GearPlug')
        body = body.replace('{number}', str(webhook.id))
        body = body.replace('{sobject}', sobject.value)
        body = body.replace('{events}', event.value)
        body = body.replace('{url}', "'" + url + "'")

        apex_trigger_response = self._client.create_apex_trigger('GearPlug', body, 'User')
        if 'success' in apex_trigger_response and apex_trigger_response['success']:
            webhook.url = url_base + url_path
            webhook.generated_id = apex_trigger_response['id']
            webhook.is_active = True
            webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            return True
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            return False

    def do_webhook_process(self, body=None, POST=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            if self.test_connection():
                self.download_source_data(event=body)
        return HttpResponse(status=200)

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() in ['sobject']:
            _tuple = tuple({'id': p, 'name': p} for p in self.get_sobject_list())
            return _tuple
        if action_specification.name.lower() in ['event']:
            _tuple = tuple({'id': p, 'name': p} for p in self.get_event_list())
            return _tuple
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def get_sobject_list(self):
        return self.cget_sobject()

    def get_event_list(self):
        return ['before insert', 'before update', 'before delete', 'after insert', 'after update', 'after delete',
                'after undelete']

    @property
    def has_webhook(self):
        return True


class HubSpotController(BaseController):
    _token = None
    _refresh_token = None
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(HubSpotController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(HubSpotController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
                self._refresh_token = self._connection_object.refresh_token
                self._client = HubSpotClient(self._token)
            except Exception as e:
                print("Error getting the hubspot token")

    def test_connection(self):
        try:
            self._client.contacts.get_contacts()
            return self._token is not None and self._refresh_token is not None
        except:
            try:
                _refresh = self.get_refresh_token()
                if _refresh is True:
                    return self._token is not None and self._refresh_token is not None
                else:
                    return self._token is None
            except:
                return self._token is None

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, **kwargs):
        action = self._plug.action.name
        new_data = []
        data = self.get_data(action)
        _id_name = self.get_id(action)
        for item in data:
            _new_item = self.get_item(action, item[_id_name])
            _new_item['properties']['createdate']['value'] = datetime.datetime.fromtimestamp(int(_new_item['properties']['createdate']['value']) / 1000)
            if last_source_record is not None:
                if _new_item['properties']['createdate']['value'] > last_source_record:
                    _new = True
                else:
                    _new = False
            else:
                _new = True
            if _new is True:
                q = StoredData.objects.filter(
                    connection=connection_object.connection,
                    plug=plug,
                    object_id=item[_id_name])
                if not q.exists():
                    for k,v in _new_item['properties'].items():
                        new_data.append(
                            StoredData(
                                name=k,
                                value=v['value'],
                                object_id=item[_id_name],
                                connection=connection_object.connection,
                                plug=plug))
            result_list = []
            if new_data:
                for data in new_data:
                    try:
                        data.save()
                        _is_stored = True
                    except:
                        _is_stored = False
                result_list.append({'identifier': {'name': _id_name, 'value': item[_id_name]}, 'is_stored': _is_stored, 'raw': ''.join(_new_item['properties'])})
            return {'downloaded_data': result_list, 'last_source_record':_new_item['properties']['createdate']['value']}

    def get_item(self, action, _id):
        if (action == 'new contact'):
            result = self._client.contacts.get_contact(_id).json()
        elif (action == 'new company'):
            result = self._client.companies.get_company(_id).json()
        elif (action == 'new deal'):
            result = self._client.deals.get_deal(_id).json()
        return result

    def get_data(self, action):
        if (action == 'new contact'):
            result = self._client.contacts.get_recently_created_contacts(30).json()['contacts']
        elif (action == 'new company'):
            result = self._client.companies.get_recently_created_companies(30).json()['results']
        elif (action == 'new deal'):
            result = self._client.deals.get_recently_created_deals(30).json()['results']
        else:
            print ("This action don't belong to this controller")
            return None
        return result

    def get_mapping_fields(self):
        action = self._plug.action.name
        actions = {'create contact': 'email', 'create company': 'name', 'create deal': 'dealname'}
        fields = self.get_target_fields()
        for f in fields:
            if f["name"] == actions[action]:
                f['required'] = True
            else:
                f['required'] = False
        return [MapField(f, controller=ConnectorEnum.HubSpot) for f in fields]

    def get_target_fields(self, **kwargs):
        action = self._plug.action.name
        actions = {'create contact': 'contacts', 'create company' : 'companies', 'create deal': 'deals'}
        response = self._client.fields.get_fields(actions[action]).json()
        return [
            i for i in response if "label" in i and i['readOnlyValue'] == False
        ]

    def send_stored_data(self, data_list):
        result_list = []
        action = self._plug.action.name
        for item in data_list:
            try:
                response = self.insert_data(item, action)
                sent = True
            except Exception as e:
                print(e)
                sent = False
            result_list.append({'data': dict(item), 'response': response['response'], 'sent': sent, 'identifier': response['id']})
        return result_list

    def insert_data(self, data, action):
        if (action == 'create contact'):
            response = self._client.contacts.create_contact(data).json()
            _id = response['vid']
        elif (action == 'create company'):
            response = self._client.companies.create_company(data).json()
            _id = response['companyId']
        elif (action == 'create deal'):
            response = self._client.deals.create_deal(data).json()
            _id = response['dealId']
        return {'id': _id, 'response': response}

    def get_id(self, action):
        if (action == 'new contact'):
            _id_name = 'vid'
        elif (action == 'new company'):
            _id_name = 'companyId'
        elif (action == 'new deal'):
            _id_name = 'dealId'
        return _id_name

    def get_refresh_token(self):
        data = {
            'client_id': settings.HUBSPOT_CLIENT_ID,
            'client_secret': settings.HUBSPOT_CLIENT_SECRET,
            'redirect_uri': settings.HUBSPOT_REDIRECT_URI,
            'refresh_token': self._refresh_token
        }
        try:
            response = self._client.get_refresh_token(data).json()
        except:
            return False
        self._connection_object.token = response['access_token']
        self._connection_object.refresh_token = response['refresh_token']
        self._connection_object.save()
        return True

        # Aunque la API de hubspot cuenta con webhooks, estos no se implementaron debido a que no se pueden crear con
        # el token, para crear un webhook se requiere autenticación del portal para developers es decir un (hapikey).
        # Los webhooks son configurados en el setting del portal, y las notificaciones son enviadas el mismo.
        # No es posible configurar las notificaciones del webhook para un portal especifico.
        #  Documentacion: https://integrate.hubspot.com/t/how-to-do-oauth2-for-app/5591

        # @property
        # def has_webhook(self):
        #     return True


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
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(ActiveCampaignController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(ActiveCampaignController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._client = ActiveCampaignClient(self._connection_object.host,
                                                    self._connection_object.connection_access_key)
            except Exception as e:
                print(e)

    def test_connection(self):
        try:
            self._client.account.get_account_info()
            return True
        except:
            return False

    def get_custom_fields(self):
        try:
            result = self._client.lists.get_list_field()
            return {str(int(v['id']) - 1): {'name': v['perstag'], 'id': v['id'], 'label': v['title']} for (k, v) in
                    result.items() if k not in ['result_code', 'result_output', 'result_message']}
        except:
            return {}

    def get_lists(self):
        _lists = self._client.lists.get_lists()
        return [_lists[value] for value in _lists if type(_lists[value]) == dict]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        try:
            if action_specification.name.lower() == 'list':
                return tuple({'id': i['id'], 'name': i['name']} for i in self.get_lists())
        except Exception as e:
            print(e)

    def create_webhook(self):
        action_name = self._plug.action.name
        if action_name == 'new subscriber' or action_name == 'unsubscribed contact':
            _select = self._plug.plug_action_specification.get(action_specification__name='list')
            _value = {'lists[{0}]'.format(_select): _select.value}
            if action_name == 'unsubscribed contact':
                action = 'unsubscribe'
            if action_name == 'new subscriber':
                action = 'subscribe'
        elif action_name == 'new contact':
            _value = {'lists[{0}]'.format(0): 0}
            action = 'subscribe'
        elif action_name == 'new task':
            _value = None
            action = 'deal_task_add'
        elif action_name == 'new deal':
            _value = None
            action = 'deal_add'
        elif action_name == 'task completed':
            _value = None
            action = 'deal_task_complete'
        elif action_name == 'deal updated':
            _value = None
            action = 'deal_update'
        webhook = Webhook.objects.create(name='activecampaign', url='',
                                         plug=self._plug, expiration='')
        url_base = settings.WEBHOOK_HOST
        url_path = reverse('home:webhook',
                           kwargs={'connector': 'activecampaign',
                                   'webhook_id': webhook.id})
        url = url_base + url_path
        post_array = {
            "name": "GearPlug WebHook",
            "url": url,
            "action": action,
            "init": "admin"
        }
        if _value is not None:
            for k, v in _value.items():
                post_array[k] = v
        try:
            response = self._client.webhooks.create_webhook(post_array)
            _created = True
        except Exception as e:
            print(e)
            _created = False

        if _created is True:
            webhook.url = url_base + url_path
            webhook.generated_id = response['id']
            webhook.is_active = True
            webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            return _created
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            return _created

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

    def send_stored_data(self, data_list):
        extra = {'controller': 'activecampaign'}
        action = self._plug.action.name
        result_list = []
        for item in data_list:
            if action == 'create contact':
                try:
                    _result = self._client.contacts.create_contact(item)
                    _sent = True
                except Exception as e:
                    _sent = False
            elif action == 'subscribe contact':
                _list_id = self._plug.plug_action_specification.get(action_specification__name='list').value
                item['p[{0}]'.format(_list_id)] = _list_id
                try:
                    _result = self._client.contacts.create_contact(item)
                    _sent = True
                except Exception as e:
                    _sent = False
            elif action == 'unsubscribe contact':
                _list_id = self._plug.plug_action_specification.get(action_specification__name='list').value
                data = self._client.contacts.view_contact_email(item['email'])
                data['p[{0}]'.format(_list_id)] = _list_id
                data['status[{0}]'.format(_list_id)] = 2
                try:
                    _result = self._client.contacts.edit_contact(data)
                    _sent = True
                except Exception as e:
                    _sent = False
            if _sent is True:
                identifier = _result['subscriber_id']
                _response = _result
            else:
                identifier = ""
                _response = e
            result_list.append({'data': dict(item), 'response': _response, 'sent': _sent, 'identifier': identifier})
        return result_list

    def download_to_stored_data(self, connection_object=None, plug=None, data=None, **kwargs):
        action = self._plug.action.name
        new_data = []
        if data is not None:
            if action in ['new contact', 'new subscriber', 'unsubscribed contact']:
                object_id = int(data['contact_id'])
            elif action in ['new task', 'task completed']:
                _user = self._client.users.view_user(data['deal_owner'])
                data['deal_owner_first_name'] = _user['first_name']
                data['deal_owner_last_name'] = _user['last_name']
                data['deal_owner_email'] = _user['email']
                data['deal_owner_username'] = _user['username']
                object_id = int(data['task_id'])
            elif action in ['new deal', 'deal updated']:
                _user = self._client.users.view_user(data['deal_owner'])
                data['deal_owner_email'] = _user['email']
                object_id = int(data['deal_id'])
            q = StoredData.objects.filter(object_id=object_id, connection=connection_object.id, plug=plug.id)
            if not q.exists():
                for k, v in data.items():
                    new_data.append(
                        StoredData(name=k, value=v or '', object_id=object_id, connection=connection_object.connection,
                                   plug=plug))
            is_stored = False
            if new_data:
                for i, item in enumerate(new_data):
                    try:
                        item.save()
                        is_stored = True
                    except Exception as e:
                        print(e)
            result_list = [{'raw': data, 'is_stored': is_stored, 'identifier': {'name': 'id', 'value': object_id}}]
            return {'downloaded_data': result_list, 'last_source_record': object_id}
        return False

    def do_webhook_process(self, body=None, POST=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
        # if 'list' in POST and POST['list'] == '0' and action_name not in ['new contact', 'new task', 'new deal']:
        #     # ActiveCampaign envia dos webhooks, el primero es cuando se crea el contacto, el segundo cuando el contacto
        #     # creado es agregado a una lista. Cuando el contacto es agregado a una lista el webhook incluye los custom
        #     # fields por eso descartamos los webhooks de contactos que no hayan sido agregados a una lista (list = 0).
        #     return HttpResponse(status=200)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            # expr = '\[(\w+)\](?:\[(\d+)\])?'
            clean_data = {}
            for k, v in POST.items():
                if "[" in k:
                    m = k.split("[")
                    key = m[0] + "_" + m[1].replace("]", "")
                    if key == 'contact_fields':
                        custom_fields = self.get_custom_fields()
                        key = custom_fields[str(int(m[2].replace("]", "")) - 1)]['label']
                    clean_data[key] = v
                else:
                    clean_data[k] = v
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
            if self.test_connection():
                self.download_source_data(data=clean_data)
                webhook.plug.save()
        return HttpResponse(status=200)

    @property
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
                raise ControllerError(code=1001, controller=ConnectorEnum.OdooCRM,
                                      message='The attributes necessary to make the connection were not obtained.. {}'.format(str(e)))
        else:
            raise ControllerError(code=1002, controller=ConnectorEnum.OdooCRM,
                                      message='The controller is not instantiated correctly.')
        if self._url is not None and self._database is not None and self._user is not None and self._password is not None:
            try:
                self._client = OdooCRMClient(self._url, self._database, self._user, self._password)
            except requests.exceptions.MissingSchema:
                raise ControllerError(code=1003, controller=ConnectorEnum.OdooCRM,
                                      message='Missing Schema.')
            except InvalidLogin as e:
                raise ControllerError(code=1003, controller=ConnectorEnum.OdooCRM,
                                      message='Invalid login. {}'.format(str(e)))
            except Exception as e:
                raise ControllerError(code=1003, controller=ConnectorEnum.OdooCRM,
                                      message='Error in the instantiation of the client.. {}'.format(str(e)))

    def test_connection(self):
        """
        Debido a la falta de un metodo mas apropiado, se decidio utilizar el metodo list_fields_partner()
        para verificar la conexion con el servidor.
        :return:
        """
        try:
            response = self._client.list_fields_partner()
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.OdooCRM,
            # message='Error in the connection test. {}'.format(str(e)))
            return False
        if response is not None and isinstance(response, dict):
            return True
        else:
            return False

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


class BatchbookController(BaseController):
    _account_name = None
    _api_key = None
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(BatchbookController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(BatchbookController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._account_name = self._connection_object.account_name
                self._api_key = self._connection_object.access_key
                self._client = ClientBatchbook(api_key=self._api_key, account_name=self._account_name)
            except Exception as e:
                print(e)
                raise

    def test_connection(self):
        try:
            self._client.get_contacts()
            return self._api_key is not None
        except:
            return None

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, **kwargs):
        if last_source_record:
            contacts = self._client.get_contacts(since=last_source_record)
        else:
            contacts = self._client.get_contacts()
        new_data = []
        for contact in contacts:
            q = StoredData.objects.filter(
                connection=connection_object.connection,
                plug=plug,
                object_id=contact['id'])
            if not q.exists():
                for k, v in contact.items():
                    if type(v) is list:
                        for dic in v:
                            for kk, vv in dic.items():
                                new_data.append(
                                    StoredData(
                                        name=kk,
                                        value=vv or '',
                                        object_id=contact['id'],
                                        connection=connection_object.connection,
                                        plug=plug))
                    else:
                        new_data.append(
                            StoredData(
                                name=k,
                                value=v or '',
                                object_id=contact['id'],
                                connection=connection_object.connection,
                                plug=plug))
        result_list = []
        _obj = ""
        if new_data:
            for item in new_data:
                is_stored = False
                try:
                    item.save()
                    is_stored = True
                except Exception as e:
                    break
                if item.name == "created_at":
                    last_source_record = item.value
                if _obj != item.object_id:
                    for contact in contacts:
                        if contact['id'] == item.object_id:
                            raw = contact
                            _obj = item.object_id
                            result_list.append(
                                {'identifier': {'name': 'id', 'value': item.object_id}, 'is_stored': is_stored,
                                 'raw': raw})
        return {'downloaded_data': result_list, 'last_source_record': last_source_record}

    def get_target_fields(self, **kwargs):
        return [
            {'name': 'prefix', 'label': 'Prefix', 'type': 'varchar', 'required': False},
            {'name': 'first_name', 'label': 'First Name', 'type': 'varchar', 'required': True},
            {'name': 'middle_name', 'label': 'Middle Name', 'type': 'varchar', 'required': False},
            {'name': 'last_name', 'label': 'Last Name', 'type': 'varchar', 'required': True},
        ]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Batchbook) for f in fields]

    def send_stored_data(self, data_list):
        result_list = []
        for item in data_list:
            data = self.create_data(item)
            try:
                response = self._client.create_contact(data=data)
            except:
                response = ""
                sent = False
                identifier = ""
            if 'id' in response:
                sent = True
                identifier = response['id']
            result_list.append({'data': dict(item), 'response': response, 'sent': sent, 'identifier': identifier})
        return result_list

    def create_data(self, item):
        return {"person": item}


class ActEssentialsController(BaseController):
    client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(ActEssentialsController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(ActEssentialsController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self.client = ActCRMClient(self._connection_object.api_key, settings.ACTESSENTIALS_DEVELOPER_KEY)
            except Exception as e:
                raise ControllerError(code=1003, controller=ConnectorEnum.ActEssentials,
                                      message='Error in the instantiation of the client. {}'.format(str(e)))
        else:
            raise ControllerError(code=1002, controller=ConnectorEnum.ActEssentials,
                                  message='The controller is not instantiated correctly.')

    def test_connection(self):
        try:
            response = self.client.get_metadata()
        except:
            # raise ControllerError(code=1004, controller=ConnectorEnum.ActEssentials,
            #                       message='Error in the connection test. {}'.format(str(e)))
            return False
        if response is not None and isinstance(response, list) and isinstance(response[0], dict) and 'id' in response:
            return True
        else:
            return False

    @property
    def has_webhook(self):
        return False

    def download_to_stored_data(self, connection_object, plug, limit=49, order_by="created desc",
                                last_source_record=None, **kwargs):
        params = {}
        if limit:
            params['top'] = limit
        if order_by:
            params['order_by'] = order_by
        if last_source_record is not None:
            params['filter'] = 'created gt {0}'.format(last_source_record)

        if plug.action.name.lower() == 'new opportunity':
            data_list = self.client.get_opportunities(**params)
        elif plug.action.name.lower() == 'new contact':
            data_list = self.client.get_contacts(**params)
        new_data = []
        for item in data_list:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                item_data = []
                for k, v in item.items():
                    item_data.append(StoredData(name=k, value=v or '', object_id=item['id'],
                                                connection=connection_object.connection, plug=plug))
                new_data.append(item_data)
        downloaded_data = []
        for new_item in new_data:
            history_obj = {'identifier': None, 'is_stored': False, 'raw': {}}
            for field in new_item:
                field.save()
                history_obj['raw'][field.name] = field.value
                history_obj['is_stored'] = True
            history_obj['identifier'] = {'name': 'id', 'value': field.object_id}
            downloaded_data.append(history_obj)
        if downloaded_data:
            return {'downloaded_data': downloaded_data, 'last_source_record': downloaded_data[0]['raw']['created']}
        return False

    def send_stored_data(self, data_list, *args, **kwargs):
        if self._plug.action.name.lower() == 'create opportunity':
            method = self.client.create_opportunity
        elif self._plug.action.name.lower() == 'create contact':
            method = self.client.create_contact
        obj_list = []
        for item in data_list:
            try:
                obj_result = {'data': dict(item)}
                result = method(**obj_result['data'])
                obj_result['response'] = result
                obj_result['identifier'] = result['id']
                obj_result['sent'] = True
            except Exception as e:
                obj_result['response'] = str(e)
                obj_result['identifier'] = '-1'
                obj_result['sent'] = False
            obj_list.append(obj_result)
        return obj_list

    def get_target_fields(self, **kwargs):
        if self._plug.action.name.lower() == 'create opportunity':
            return [
                {'name': 'title', 'label': 'title', 'type': 'varchar', 'required': True},
                {'name': 'stage', 'label': 'stage', 'type': 'varchar', 'required': True},
                {'name': 'description', 'label': 'description', 'type': 'varchar', 'required': False},
                {'name': 'total', 'label': 'total', 'type': 'varchar', 'required': False},
                {'name': 'currency', 'label': 'currency', 'type': 'varchar', 'required': False},
                {'name': 'notes', 'label': 'notes', 'type': 'varchar', 'required': False},
                {'name': 'estimatedClose', 'label': 'estimatedClose', 'type': 'varchar', 'required': False},
                {'name': 'actualClose', 'label': 'actualClose', 'type': 'varchar', 'required': False},
                {'name': 'notes', 'label': 'notes', 'type': 'varchar', 'required': False},
            ]
        elif self._plug.action.name.lower() == 'create contact':
            return [
                {'name': 'firstName', 'label': 'firstName', 'type': 'varchar', 'required': True},
                {'name': 'lastName', 'label': 'lastName', 'type': 'varchar', 'required': False},
                {'name': 'company', 'label': 'company', 'type': 'varchar', 'required': False},
                {'name': 'jobTitle', 'label': 'jobTitle', 'type': 'varchar', 'required': False},
                {'name': 'emailAddress', 'label': 'emailAddress', 'type': 'email', 'required': False},
                {'name': 'altEmailAddress', 'label': 'altEmailAddress', 'type': 'email', 'required': False},
                {'name': 'businessPhone', 'label': 'businessPhone', 'type': 'varchar', 'required': False},
                {'name': 'mobilePhone', 'label': 'mobilePhone', 'type': 'varchar', 'required': False},
                {'name': 'homePhone', 'label': 'homePhone', 'type': 'varchar', 'required': False},
                {'name': 'website', 'label': 'website', 'type': 'varchar', 'required': False},
                {'name': 'linkedinUrl', 'label': 'linkedinUrl', 'type': 'varchar', 'required': False},
                {'name': 'birthday', 'label': 'birthday', 'type': 'varchar', 'required': False},
            ]

    def get_mapping_fields(self, **kwargs):
        return [MapField(f, controller=ConnectorEnum.ActEssentials) for f in self.get_target_fields()]


class AgileCRMController(BaseController):
    _api_key = None
    _email = None
    _domain = None
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(AgileCRMController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(AgileCRMController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._api_key = self._connection_object.api_key
                self._email = self._connection_object.email
                self._domain = self._connection_object.domain
            except AttributeError as e:
                raise ControllerError(code=1, controller=ConnectorEnum.AgileCRM,
                                      message='Error getting the AgileCRM attributes args. {}'.format(str(e)))
        else:
            raise ControllerError('No connection.')
        if self._api_key is not None and self._email is not None and self._domain is not None:
            try:
                self._client = AgileCRMClient(self._api_key, self._email, self._domain)
            except requests.exceptions.MissingSchema:
                raise
            except InvalidLogin as e:
                raise ControllerError(code=2, controller=ConnectorEnum.AgileCRM,
                                      message='Invalid login. {}'.format(str(e)))

    def test_connection(self):
        return self._client.get_contacts({'page_size': 1}) is not None

    def has_webhook(self):
        return None

    def search_contact(self, query):
        try:
            if query:
                return self._client.search_contact(query)
            else:
                return self._client.get_contacts()
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.AgileCRM, message='Error. {}'.format(str(e)))

    def get_list_fields(self):
        return [
            {
                'name': 'type',
                'required': False,
                'type': 'list',
                'choices': ['PERSON', 'COMPANY']
            }, {
                'name': 'tags',
                'required': False,
                'type': 'string',
            }, {
                'name': 'lead_score',
                'required': False,
                'type': 'integer'
            }, {
                'name': 'contact_company_id',
                'required': False,
                'type': 'long'
            }, {
                'name': 'star_value',
                'required': False,
                'type': 'short'
            }, {
                'name': 'campaignStatus',
                'required': False,
                'type': 'list'
            }, {
                'name': 'first_name',
                'required': True,
                'type': 'string'
            }, {
                'name': 'last_name',
                'required': False,
                'type': 'string'
            }, {
                'name': 'company',
                'required': False,
                'type': 'string'
            }, {
                'name': 'title',
                'required': False,
                'type': 'string'
            }, {
                'name': 'email',
                'required': False,
                'type': 'string'
            }, {
                'name': 'address',
                'required': False,
                'type': 'string'
            }, {
                'name': 'phone',
                'required': False,
                'type': 'string'
            }, {
                'name': 'website',
                'required': False,
                'type': 'string'
            }, {
                'name': 'image',
                'required': False,
                'type': 'string'
            }, {
                'name': 'unsubscribeStatus',
                'required': False,
                'type': 'list'
            }, {
                'name': 'emailBounceStatus',
                'required': False,
                'type': 'list'
            }, {
                'name': 'tags',
                'required': False,
                'type': 'list'
            }
        ]

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
        query = None
        if last_source_record is not None:
            today = datetime.datetime.today().timestamp()
            query = {"rules": [{"LHS": "created_time", "CONDITION": "BETWEEN", "RHS": int(last_source_record) * 1000,
                                "RHS_NEW": int(today) * 1000}], "contact_type": "PERSON"}
        params = None
        if query:
            params = {
                'page_size': 25,
                'global_sort_key': '-created_time',
                'filterJson': json.dumps(query)
            }
        entries = self.search_contact(params)

        raw_data = []
        new_data = []
        for _item in entries:
            item = self.get_fields_from_properties(_item)
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
            return {'downloaded_data': result_list, 'last_source_record': result_list[0]['raw']['created_time']}
        return False

    def get_fields_from_properties(self, _dict):
        properties = _dict.pop('properties')
        for i in properties:
            _dict[i['name']] = i['value']
        return _dict

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                res = self.set_entry(dict(item))
                obj_result['response'] = res
                obj_result['sent'] = True
                obj_result['identifier'] = res['id']
            except Exception as e:
                obj_result['response'] = str(e)
                obj_result['sent'] = False
                obj_result['identifier'] = '-1'
            obj_list.append(obj_result)
        return obj_list

    def set_entry(self, item):
        try:
            item['properties'] = []
            _fields = ['first_name', 'last_name', 'image', 'company', 'title', 'email', 'phone', 'website', 'address']
            _remove = []
            for k, v in item.items():
                if k in _fields:
                    item['properties'].append({'name': k, 'type': 'SYSTEM', 'value': v})
                    _remove.append(k)
            for k in _remove:
                del item[k]
            return self._client.create_contact(item)
        except WrongParameter as e:
            raise ControllerError(code=4, controller=ConnectorEnum.AgileCRM,
                                  message='Wrong Parameter. {}'.format(str(e)))
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.SugarCRM, message='Error. {}'.format(str(e)))

    def get_mapping_fields(self, **kwargs):
        fields = self.get_list_fields()
        return [MapField(f, controller=ConnectorEnum.AgileCRM) for f in fields]

    def get_action_specification_options(self, action_specification_id):
        pass
