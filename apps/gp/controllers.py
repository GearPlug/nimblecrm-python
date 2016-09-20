from apps.gp.models import StoredData
from apiconnector.settings import FACEBOOK_APP_SECRET, FACEBOOK_APP_ID, FACEBOOK_GRAPH_VERSION
import facebook
import json
import requests
import hmac
import hashlib
import logging
import MySQLdb
import copy
import sugarcrm

logger = logging.getLogger('controller')


class CustomSugarObject(sugarcrm.SugarObject):
    module = "CustomObject"

    def __init__(self, *args, **kwargs):
        if args:
            self.module = args[0]
        return super(CustomSugarObject, self).__init__(**kwargs)

    @property
    def query(self):
        return ''


class SugarCRMController(object):
    user = None
    password = None
    url = None
    connection_object = None
    session = None
    plug = None
    module = None

    def __init__(self, *args, **kwargs):
        self.create_connection(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            try:
                self.connection_object = args[0]
                self.user = self.connection_object.connection_user
                self.password = self.connection_object.connection_password
                self.url = self.connection_object.url
            except:
                print("Error gettig the SugarCRM attributes")
            try:
                self.plug = args[1]
            except:
                print(
                    "Error:SugarCRMController with connection: %s has no plug." % self.connection_object.connection.id)
            try:
                self.module = args[2]
            except:
                print('Error:SugarCRMController. No module defined.')
        elif kwargs:
            try:
                self.url = kwargs.pop('url', 'url')
                self.user = kwargs.pop('connection_user', 'usuario')
                self.password = kwargs.pop('connection_password', 'clave')
            except:
                print("Error gettig the SugarCRM attributes")
        if self.url is not None and self.user is not None and self.password is not None:
            self.session = sugarcrm.Session(self.url, self.user, self.password)
        return self.session is not None and self.session.session_id is not None

    def get_available_modules(self):
        return self.session.get_available_modules()

    def get_entries(self, module_name, id_list):
        return self.session.get_entries(module_name, id_list)

    def get_entry_list(self, module, **kwargs):
        custom_module = CustomSugarObject(module)
        return self.session.get_entry_list(custom_module, **kwargs)

    def get_module_fields(self, module, **kwargs):
        custom_module = CustomSugarObject(module)
        return self.session.get_module_fields(custom_module, **kwargs)

    def download_module_to_stored_data(self, connection_object, plug, module):
        data = self.get_entry_list(module)
        stored_data = [(item.connection, item.object_id, item.name) for item in
                       StoredData.objects.filter(connection=connection_object.connection, plug=plug)]
        new_data = []
        for item in data:
            for column in item.fields:
                if (connection_object.connection, item.id, column['name']) not in stored_data:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=item.id,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            StoredData.objects.bulk_create(new_data)
        return True if new_data else False

    def download_source_data(self):
        if self.connection_object is not None and self.plug is not None and self.module is not None:
            self.download_module_to_stored_data(self.connection_object, self.plug, self.module)
        else:
            print("Error, there's no connection or plug")

    def set_entry(self, obj):
        return self.session.set_entry(obj)

    def set_entries(self, obj_list):
        return self.session.set_entries(obj_list)

    def send_stored_data(self, source_data):
        if self.plug is not None:
            module_name = self.plug.plug_specification.all()[0].value
            obj_list = []
            for item in source_data:
                obj_list.append(CustomSugarObject(module_name, **item['data']))
            return self.set_entries(obj_list)
        raise ControllerError


class FacebookController(object):
    app_id = FACEBOOK_APP_ID
    app_secret = FACEBOOK_APP_SECRET
    base_graph_url = 'https://graph.facebook.com'
    connection_object = None
    plug = None

    def __init__(self, *args, **kwargs):
        if args:
            self.connection_object = args[0]
            try:
                self.plug = args[1]
            except:
                print("Error:FacebookController with connection: %s has no plug" % self.connection_object.connection.id)

    # Does a facebook request. Returns an array with the response or an empty array
    def send_request(self, url='', token='', base_url='', params=[]):
        if not base_url:
            base_url = self.base_graph_url
        if not params:
            params = {'access_token': token,
                      'appsecret_proof': self.get_app_secret_proof(token)}
        graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)
        graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
        r = requests.get('%s/v%s/%s' % (base_url, FACEBOOK_GRAPH_VERSION, url),
                         params=params)
        # logger.info('Facebook Controller >> Request sent: %s' % r.url)
        try:
            return json.loads(r.text)['data']
        except KeyError:
            return r
        except Exception as e:
            print(e)
            return []

    def extend_token(self, token):
        url = 'oauth/access_token'
        params = {'grant_type': 'fb_exchange_token',
                  'client_id': FACEBOOK_APP_ID,
                  'client_secret': FACEBOOK_APP_SECRET,
                  'fb_exchange_token': token}
        r = self.send_request(url=url, params=params)
        # logger.info('Facebook Controller >> Token extend: %s' % r.url)
        try:
            return json.loads(r.text)['access_token']
        except Exception as e:
            print(e)
            return ''

    def get_app_secret_proof(self, access_token):
        h = hmac.new(
            self.app_secret.encode('utf-8'),
            msg=access_token.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        return h.hexdigest()

    def get_pages(self, access_token):
        url = 'me/accounts'
        return self.send_request(url=url, token=access_token)

    def get_leads(self, access_token, form_id):
        url = '%s/leads' % form_id
        return self.send_request(url=url, token=access_token)

    def download_leads_to_stored_data(self, connection_object, plug):
        if plug is None:
            plug = self.plug
        leads = self.get_leads(connection_object.token, connection_object.id_form)
        stored_data = [(item.connection, item.object_id, item.name) for item in
                       StoredData.objects.filter(connection=connection_object.connection, plug=plug)]
        new_data = []
        for item in leads:
            new_data = new_data + [StoredData(name=lead['name'], value=lead['values'][0], object_id=item['id'],
                                              connection=connection_object.connection, plug=plug)
                                   for lead in item['field_data'] if
                                   (connection_object.connection, item['id'], lead['name']) not in stored_data]
        logger.info('Facebook Controller >> NEW LEADS for connection id:%s  Number of entries: %s' % (
            connection_object.connection.id, len(new_data)))
        if new_data:
            StoredData.objects.bulk_create(new_data)

    def download_source_data(self):
        if self.connection_object is not None and self.plug is not None:
            self.download_leads_to_stored_data(self.connection_object, self.plug)
        else:
            print("Error, there's no connection or plug")


class MySQLController(object):
    connection_object = None
    connection = None
    cursor = None
    database = None
    table = None
    plug = None

    def __init__(self, *args, **kwargs):
        self.create_connection(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            try:
                self.connection_object = args[0]
                host = self.connection_object.host
                port = self.connection_object.port
                user = self.connection_object.connection_user
                password = self.connection_object.connection_password
                self.database = self.connection_object.database
                self.table = self.connection_object.table
            except:
                print("Error gettig the MySQL attributes")
                pass
            try:
                self.plug = args[1]
            except:
                print(
                    "Error:MySQLController with connection: %s has no plug." % self.connection_object.connection.id)
        elif kwargs:
            try:
                host = kwargs.pop('host', 'host')
                port = kwargs.pop('port', 'puerto')
                user = kwargs.pop('connection_user', 'usuario')
                password = kwargs.pop('connection_password', 'clave')
                self.database = kwargs.pop('database', 'database')
                self.table = kwargs.pop('table', 'table')
            except:
                print("Error gettig the MySQL attributes")
                pass
        try:
            self.connection = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=self.database)
            self.cursor = self.connection.cursor()
        except:
            self.connection = None
        return self.connection is not None

    def set_cursor(self):
        if self.connection is not None:
            try:
                self.cursor = self.connection.cursor()
                return True
            except:
                print("Error getting cursor")
                return None
        else:
            print("Error no connection")
            return None

    def get_cursor(self):
        return self.cursor

    def describe_table(self):
        if self.table is not None and self.database is not None:
            try:
                self.cursor.execute('DESCRIBE `%s`.`%s`' % (self.database, self.table))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2], 'is_primary': item[3] == 'PRI'} for
                        item in self.cursor]
            except:
                print('Error ')
        return []

    def get_primary_keys(self):
        if self.table is not None and self.database is not None:
            try:
                self.cursor.execute('DESCRIBE `%s`.`%s`' % (self.database, self.table))
                return [item[0] for item in self.cursor if item[3] == 'PRI']
            except:
                print('Error ')
        return None

    def select_all(self):
        if self.table is not None and self.database is not None:
            try:
                self.cursor.execute('SELECT * FROM `%s`.`%s`' % (self.database, self.table))
                cursor_select_all = copy.copy(self.cursor)
                self.describe_table()
                cursor_describe = self.cursor
                return [{column[0]: item[i] for i, column in enumerate(cursor_describe)} for item in cursor_select_all]
            except:
                print('Error ')
        return []

    def download_to_stored_data(self, connection_object, plug):
        if plug is None:
            plug = self.plug
        source_data = self.select_all()
        stored_data = [(item.connection.id, item.object_id, item.name) for item in
                       StoredData.objects.filter(connection=connection_object.connection, plug=plug)]
        id_list = self.get_primary_keys()
        parsed_source_data = [{'id': tuple(item[key] for key in id_list),
                               'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]}
                              for item in source_data]

        new_data = []
        new_data = new_data + [StoredData(name=item['name'], value=item['value'], object_id=row['id'][0],
                                          connection=connection_object.connection, plug=plug)
                               for row in parsed_source_data for item in row['data'] if
                               (connection_object.connection.id, str(row['id'][0]), item['name']) not in stored_data]
        # logger.info('MySQL Controller >> NEW ROWs for connection id:%s  Number of entries: %s' % (
        #     connection_object.connection.id, len(new_data)))
        if new_data:
            StoredData.objects.bulk_create(new_data)

    def download_source_data(self):
        if self.connection_object is not None and self.plug is not None:
            self.download_to_stored_data(self.connection_object, self.plug)
        else:
            print("Error, there's no connection or plug")
            # print("\n----------------------\n")


class MailChimpController(object):
    pass


class ControllerError(Exception):
    pass
