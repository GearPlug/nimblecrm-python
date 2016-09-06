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

logger = logging.getLogger('controller')


class FacebookController(object):
    app_id = FACEBOOK_APP_ID
    app_secret = FACEBOOK_APP_SECRET
    base_graph_url = 'https://graph.facebook.com'

    def __init__(self, *args, **kwargs):
        pass

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

    def download_leads_to_stored_data(self, connection):
        leads = self.get_leads(connection.token, connection.id_form)
        stored_data = [(item.connection, item.object_id, item.name) for item in
                       StoredData.objects.filter(connection=connection.connection)]
        new_data = []
        for item in leads:
            new_data = new_data + [StoredData(name=lead['name'], value=lead['values'][0], object_id=item['id'],
                                              connection=connection.connection)
                                   for lead in item['field_data'] if
                                   (connection.connection, item['id'], lead['name']) not in stored_data]
        logger.info('Facebook Controller >> NEW LEADS for connection: %s' % connection.id)
        StoredData.objects.bulk_create(new_data)


class MySQLController(object):
    connection = None
    cursor = None
    database = None
    table = None

    def __init__(self, *args, **kwargs):
        self.create_connection(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            try:
                connection = args[0]
                host = connection.host
                port = connection.port
                user = connection.connection_user
                password = connection.connection_password
                self.database = connection.database
                self.table = connection.table
            except:
                print("Error gettig the MySQL attributes")
                pass
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

    def download_to_stored_data(self, connection_object):
        data = self.select_all()
        stored_data = [(item.connection, item.object_id, item.name) for item in
                       StoredData.objects.filter(connection=connection_object.connection)]
        id_list = self.get_primary_keys()
        parsed_data = [{'id': tuple(item[key] for key in id_list),
                        'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]} for
                       item in data]
        new_data = []
        new_data = new_data + [StoredData(name=item['name'], value=item['value'], object_id=row['id'][0],
                                          connection=connection_object.connection)
                               for row in parsed_data for item in row['data'] if
                               (connection_object.connection, row['id'][0], item['name']) not in stored_data]
        logger.info('MySQL Controller >> NEW ROWs for connection: %s' % connection_object.connection.id)
        StoredData.objects.bulk_create(new_data)
