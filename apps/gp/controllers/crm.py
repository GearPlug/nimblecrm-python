from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
import requests
import sugarcrm
import json
import string
from apps.gp.models import StoredData
from apps.gp.map import MapField
from apps.gp.enum import ConnectorEnum


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
        elif not args and kwargs:
            try:
                self._user = kwargs.pop('connection_user')
                self._password = kwargs.pop('connection_password')
                self._url = kwargs.pop('url')
            except Exception as e:
                print("Error getting the SugarCRM attributes")
        if self._url is not None and self._user is not None and self._password is not None:
            self._session = sugarcrm.Session(self._url, self._user, self._password)
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

    def download_to_stored_data(self, connection_object, plug, limit=29, order_by="date_entered DESC", **kwargs):
        module = plug.plug_specification.all()[0].value  # Especificar que specification
        data = self.get_entry_list(module, max_results=limit, order_by=order_by)
        new_data = []
        for item in data:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item.id)
            if not q.exists():
                for column in item.fields:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=item.id,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(data[0].fields)
            extra = {'controller': 'sugarcrm'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
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
            module_name = self._plug.plug_specification.all()[0].value
            extra = {'controller': 'sugarcrm'}
            for item in data_list:
                try:
                    res = self.set_entry(CustomSugarObject(module_name, **item))
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (res.id), extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (res.id), extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, module, **kwargs):
        return self.get_module_fields(module, **kwargs)


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
                    print(self._token)
                except Exception as e:
                    print("Error getting zohocrm token")
                    print(e)
        elif kwargs:
            try:
                self._token = kwargs.pop('token', None)
            except Exception as e:
                print("Error getting zohocrm token")
                print(e)
        if self._token is not None:
            response = self.get_modules()['_content'].decode()
            response = json.loads(response)
            if "result" in response["response"]:
                return self._token is not None

    def get_modules(self):
        params = {'authtoken': self._token, 'scope': 'crmapi'}
        url = "https://crm.zoho.com/crm/private/json/Info/getModules"
        return requests.get(url, params).__dict__

    def download_to_stored_data(self, connection_object, plug, ):
        module_id = self._plug.plug_specification.all()[0].value
        module_name = self.get_module_name(module_id)
        data = self.get_feeds(module_name)
        new_data = []
        for item in data:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=item[item['id']])
            if not q.exists():
                for column in item:
                    new_data.append(StoredData(name=column, value=item[column], object_id=item[item['id']],
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(data)
            extra = {'controller': 'zohocrm'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            return True
        return False

    def get_mapping_fields(self):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.ZohoCRM) for f in fields]

    def get_target_fields(self, **kwargs):
        module_id = self._plug.plug_specification.all()[0].value
        list = self.get_fields(module_id)
        fields = []
        for val in list:
            if (type(val) == dict):
                fields.append(val)
            else:
                for i in val:
                    print(type(i))
                    print(i)
        print(fields)
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
            return values
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
            module_n = module_n[: - 1]
        modules['name'] = name
        modules['id'] = module_n.upper() + 'ID'
        for d in my_dictionary['FL']:
            if ('content' in d):
                modules[d['val']] = d['content']
            else:
                for v2 in d:
                    if (v2 != 'val'): self.get_lists(d[v2], v2)
        return modules

    def get_feeds(self, module_name):
        max_result = 30
        params = {'toIndex': 30, 'authtoken': self._token, 'scope': 'crmapi', 'sortOrderString': 'desc'}
        url = "https://crm.zoho.com/crm/private/json/" + module_name + "/getMyRecords"
        response = requests.get(url, params).__dict__['_content'].decode()
        response = json.loads(response)
        response = response['response']
        if ("result" in response):
            print("result")
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
