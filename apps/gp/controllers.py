from apps.gp.models import StoredData
from apiconnector.settings import FACEBOOK_APP_SECRET, FACEBOOK_APP_ID, FACEBOOK_GRAPH_VERSION
import facebook
import json
import requests
import hmac
import hashlib
import logging
import MySQLdb
import psycopg2
import pymssql
import copy
import sugarcrm
import time
from apiclient import discovery
from mailchimp3 import MailChimp
from oauth2client import client as GoogleClient
import httplib2
from collections import OrderedDict

logger = logging.getLogger('controller')


class BaseController(object):
    """
    Abstract controller class.
    - The init calls the create_connection method.

    """
    _connection_object = None
    _plug = None
    _log = logging.getLogger('controller')

    def __init__(self, *args, **kwargs):
        self.create_connection(*args, **kwargs)

    def create_connection(self, *args):
        if args:
            self._connection_object = args[0]
            try:
                self._plug = args[1]
            except:
                pass
            return

    def send_stored_data(self, *args, **kwargs):
        raise ControllerError('Not implemented yet.')

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        raise ControllerError('Not implemented yet.')

    def download_source_data(self, **kwargs):
        if self._connection_object is not None and self._plug is not None:
            return self.download_to_stored_data(self._connection_object, self._plug, **kwargs)
        else:
            raise ControllerError("There's no active connection or plug.")

    def get_target_fields(self, **kwargs):
        raise ControllerError("Not implemented yet.")


class GoogleSpreadSheetsController(BaseController):
    _credential = None
    _spreadsheet_id = None
    _worksheet_name = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(GoogleSpreadSheetsController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    credentials_json = self._connection_object.credentials_json
                except Exception as e:
                    print("Error getting the GoogleSpreadSheets attributes 1")
                    print(e)
                    credentials_json = None
        elif not args and kwargs:
            if 'credentials_json' in kwargs:
                credentials_json = kwargs.pop('credentials_json')
        else:
            credentials_json = None
        files = None
        if credentials_json is not None:
            try:
                for s in self._plug.plug_specification.all():
                    if s.action_specification.name.lower() == 'spreadsheet':
                        self._spreadsheet_id = s.value
                    if s.action_specification.name.lower() == 'worksheet':
                        self._worksheet_name = s.value
            except:
                print("Error asignando los specifications")
            try:
                _json = json.dumps(credentials_json)
                self._credential = GoogleClient.OAuth2Credentials.from_json(_json)
                http_auth = self._credential.authorize(httplib2.Http())
                drive_service = discovery.build('drive', 'v3', http=http_auth)
                files = drive_service.files().list().execute()
            except Exception as e:
                print("Error getting the GoogleSpreadSheets attributes 2")
                self._credential = None
                files = None
        return files is not None

    def download_to_stored_data(self, connection_object, plug, *args, **kwargs):
        if plug is None:
            plug = self._plug
        if not self._spreadsheet_id or not self._worksheet_name:
            return False
        sheet_values = self.get_worksheet_values()
        new_data = []
        for idx, item in enumerate(sheet_values[1:]):
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=idx + 1)
            if not q.exists():
                for idx2, cell in enumerate(item):
                    new_data.append(StoredData(name=sheet_values[0][idx2], value=cell, object_id=idx + 1,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(sheet_values)
            extra = {'controller': 'google_spreadsheets'}
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
            # raise IndexError("hola")
            return True
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
            for obj in data_list:
                l = [val for val in obj.values()]
                obj_list.append(l)
            extra = {'controller': 'google_spreadsheets'}
            sheet_values = self.get_worksheet_values()
            for idx, item in enumerate(obj_list, len(sheet_values) + 1):
                res = self.create_row(item, idx)
            return
        raise ControllerError("Incomplete.")

    def colnum_string(self, n):
        div = n
        string = ""
        temp = 0
        while div > 0:
            module = (div - 1) % 26
            string = chr(65 + module) + string
            div = int((div - module) / 26)
        return string

    def get_sheet_list(self):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        drive_service = discovery.build('drive', 'v3', http=http_auth)
        files = drive_service.files().list().execute()
        sheet_list = tuple(
            f for f in files['files'] if 'mimeType' in f and f['mimeType'] == 'application/vnd.google-apps.spreadsheet')
        return sheet_list

    def get_worksheet_list(self, sheet_id):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        result = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        worksheet_list = tuple(i['properties'] for i in result['sheets'])
        return worksheet_list

    def get_worksheet_values(self, from_row=None, limit=None):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        res = sheets_service.spreadsheets().values().get(spreadsheetId=self._spreadsheet_id,
                                                         range='{0}'.format(self._worksheet_name)).execute()
        values = res['values']
        if from_row is None and limit is None:
            return values
        else:
            limit = limit if limit is not None else len(values) - 1
            from_row = from_row - 1 if from_row is not None else 0
            return values[from_row:from_row + limit]
        return values

    def get_worksheet_first_row(self):
        return self.get_worksheet_values(from_row=1, limit=1)[0]

    def get_worksheet_second_row(self):
        return self.get_worksheet_values(from_row=2, limit=1)[0]

    def create_row(self, row, idx):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())

        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        body = {
            'values': [row]
        }
        _range = "{0}!A{1}:{2}{1}".format(self._worksheet_name, idx, self.colnum_string(len(row)))
        res = sheets_service.spreadsheets().values().update(
            spreadsheetId=self._spreadsheet_id,
            range=_range, valueInputOption='RAW',
            body=body).execute()

        return res

    def get_target_fields(self, **kwargs):
        return self.get_worksheet_first_row(**kwargs)


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
        return [dict(m, hash_id=l['id']) for m in members for l in _list['members'] if m['email_address'] == l['email_address']]


class FacebookController(BaseController):
    _app_id = FACEBOOK_APP_ID
    _app_secret = FACEBOOK_APP_SECRET
    _base_graph_url = 'https://graph.facebook.com'
    _token = None
    _page = None
    _form = None

    def __init__(self, *args):
        super(FacebookController, self).__init__(*args)

    def create_connection(self, *args, **kwargs):
        if args:
            super(FacebookController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                except Exception as e:
                    print("Error getting the Facebook token")
                    # raise
        elif kwargs:
            try:
                self._token = kwargs.pop('token')
            except Exception as e:
                print("Error getting the Facebook token")

        try:
            for s in self._plug.plug_specification.all():
                if s.action_specification.name.lower() == 'page':
                    self._page = s.value
                if s.action_specification.name.lower() == 'form':
                    self._form = s.value
        except:
            print("Error asignando los specifications")

        try:
            object_list = self.get_account(self._token).json()
            if 'id' in object_list:
                return True
        except Exception as e:
            return False
        return False

    def _get_app_secret_proof(self, access_token):
        h = hmac.new(
            self._app_secret.encode('utf-8'),
            msg=access_token.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        return h.hexdigest()

    def _send_request(self, url='', token='', base_url='', params=[], from_date=None):
        if not base_url:
            base_url = self._base_graph_url
        if not params:
            params = {'access_token': token,
                      'appsecret_proof': self._get_app_secret_proof(token)}
        if from_date is not None:
            params['from_date'] = from_date
        graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)
        graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
        r = requests.get('%s/v%s/%s' % (base_url, FACEBOOK_GRAPH_VERSION, url),
                         params=params)
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
                  'client_id': self._app_id,
                  'client_secret': self._app_secret,
                  'fb_exchange_token': token}
        r = self._send_request(url=url, params=params)
        try:
            return json.loads(r.text)['access_token']
        except Exception as e:
            print(e)
            return ''

    def get_account(self, access_token):
        url = 'me'
        return self._send_request(url=url, token=access_token)

    def get_pages(self, access_token):
        url = 'me/accounts'
        return self._send_request(url=url, token=access_token)

    def get_leads(self, access_token, form_id, from_date=None):
        url = '%s/leads' % form_id
        return self._send_request(url=url, token=access_token, from_date=from_date)

    def get_forms(self, access_token, page_id):
        url = '%s/leadgen_forms' % page_id
        return self._send_request(url=url, token=access_token)

    def download_to_stored_data(self, connection_object, plug, from_date=None):
        if plug is None:
            plug = self._plug
        if from_date is not None:
            from_date = int(time.mktime(from_date.timetuple()) * 1000)
            # print('from_date: %s' % from_date)

        leads = self.get_leads(connection_object.token, self._form, from_date=from_date)
        new_data = []
        for item in leads:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                for column in item['field_data']:
                    new_data.append(StoredData(name=column['name'], value=column['values'][0], object_id=item['id'],
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(leads[0]['field_data'])
            entries = len(new_data) // field_count
            extra = {'controller': 'facebook'}
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


class MySQLController(BaseController):
    _connection = None
    _database = None
    _table = None
    _cursor = None

    def __init__(self, *args, **kwargs):
        super(MySQLController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MySQLController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    pass
                    # raise
                    print("Error getting the MySQL attributes")
        elif not args and kwargs:
            try:
                host = kwargs.pop('host')
                port = kwargs.pop('port')
                user = kwargs.pop('connection_user')
                password = kwargs.pop('connection_password')
                self._database = kwargs.pop('database')
                self._table = kwargs.pop('table', None)
            except Exception as e:
                pass
                # raise
                print("Error getting the MySQL attributes")
        try:
            self._connection = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=self._database)
            self._cursor = self._connection.cursor()
        except:
            self._connection = None
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute('DESCRIBE `%s`.`%s`' % (self._database, self._table))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2], 'is_primary': item[3] == 'PRI'} for
                        item in self._cursor]
            except:
                print('Error describing table: %s')
        return []

    def get_primary_keys(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute('DESCRIBE `%s`.`%s`' % (self._database, self._table))
                return [item[0] for item in self._cursor if item[3] == 'PRI']
            except:
                print('Error ')
        return None

    def select_all(self, limit=50):
        if self._table is not None and self._database is not None and self._plug is not None:
            try:
                order_by = self._plug.plug_specification.all()[0].value
            except:
                order_by = None
            select = 'SELECT * FROM `%s`.`%s`' % (self._database, self._table)
            if order_by is not None:
                select += 'ORDER BY %s DESC ' % order_by
            if limit is not None and isinstance(limit, int):
                select += 'LIMIT %s' % limit
            try:
                self._cursor.execute(select)
                cursor_select_all = copy.copy(self._cursor)
                self.describe_table()
                cursor_describe = self._cursor
                return [{column[0]: item[i] for i, column in enumerate(cursor_describe)} for item in cursor_select_all]
            except Exception as e:
                print(e)
        return []

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        if plug is None:
            plug = self._plug
        data = self.select_all()
        id_list = self.get_primary_keys()
        parsed_data = [{'id': tuple(item[key] for key in id_list),
                        'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]}
                       for item in data]
        new_data = []
        for item in parsed_data:
            try:
                id_item = item['id'][0]
            except IndexError:
                id_item = None
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id_item)
            if not q.exists():
                for column in item['data']:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=id_item,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(parsed_data[0]['data'])
            extra = {'controller': 'postgresql'}
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

    def _get_insert_statement(self, item):
        insert = """INSERT INTO `%s`(%s) VALUES (%s)""" % (
            self._table, """,""".join(item.keys()), """,""".join("""\"%s\"""" % i for i in item.values()))
        return insert

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
            extra = {'controller': 'postgresql'}
            for item in data_list:
                try:
                    insert = self._get_insert_statement(item)
                    self._cursor.execute(insert)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (self._cursor.lastrowid), extra=extra)
                    obj_list.append(self._cursor.lastrowid)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (self._cursor.lastrowid), extra=extra)
            try:
                self._connection.commit()
            except:
                self._connection.rollback()
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, **kwargs):
        return self.describe_table(**kwargs)


class PostgreSQLController(BaseController):
    _connection = None
    _database = None
    _table = None
    _cursor = None

    def __init__(self, *args, **kwargs):
        super(PostgreSQLController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(PostgreSQLController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    pass
                    # raise
                    print("Error getting the PostgreSQL attributes")
        elif not args and kwargs:
            try:
                host = kwargs.pop('host')
                port = kwargs.pop('port')
                user = kwargs.pop('connection_user')
                password = kwargs.pop('connection_password')
                self._database = kwargs.pop('database')
                self._table = kwargs.pop('table', None)
            except Exception as e:
                pass
                # raise
                print("Error getting the PostgreSQL attributes")
        try:
            self._connection = psycopg2.connect(host=host, port=int(port), user=user, password=password,
                                                database=self._database)
            self._cursor = self._connection.cursor()
        except:
            self._connection = None
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    'SELECT column_name, data_type, is_nullable FROM INFORMATION_SCHEMA.columns WHERE table_name = %s',
                    (self._table,))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for
                        item in self._cursor]
            except:
                print('Error describing table: %s')
        return []

    def get_primary_keys(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    'SELECT c.column_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name) JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema AND tc.table_name = c.table_name AND ccu.column_name = c.column_name where tc.table_name = %s',
                    (self._table,))
                return [item[0] for item in self._cursor]
            except:
                print('Error ')
        return None

    def select_all(self, limit=50):
        if self._table is not None and self._database is not None and self._plug is not None:
            try:
                order_by = self._plug.plug_specification.all()[0].value
            except:
                order_by = None
            select = 'SELECT * FROM %s ' % self._table
            if order_by is not None:
                select += 'ORDER BY %s DESC ' % order_by
            if limit is not None and isinstance(limit, int):
                select += 'LIMIT %s' % limit
            try:
                self._cursor.execute(select)
                cursor_select_all = [item for item in self._cursor]
                cursor_describe = self.describe_table()
                return [{column['name']: item[i] for i, column in enumerate(cursor_describe)} for item in
                        cursor_select_all]
            except Exception as e:
                print(e)
        return []

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        if plug is None:
            plug = self._plug
        data = self.select_all()
        id_list = self.get_primary_keys()
        parsed_data = [{'id': tuple(item[key] for key in id_list),
                        'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]}
                       for item in data]
        new_data = []
        for item in parsed_data:
            try:
                id_item = item['id'][0]
            except IndexError:
                id_item = None
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id_item)
            if not q.exists():
                for column in item['data']:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=id_item,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(parsed_data[0]['data'])
            extra = {'controller': 'postgresql'}
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

    def _get_insert_statement(self, item):
        insert = """INSERT INTO %s (%s) VALUES (%s)""" % (
            self._table, """,""".join(item.keys()), """,""".join("""\'%s\'""" % i for i in item.values()))
        return insert

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
            extra = {'controller': 'postgresql'}
            for item in data_list:
                try:
                    insert = self._get_insert_statement(item)
                    self._cursor.execute(insert)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (self._cursor.lastrowid), extra=extra)
                    obj_list.append(self._cursor.lastrowid)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (self._cursor.lastrowid), extra=extra)
            try:
                self._connection.commit()
            except:
                self._connection.rollback()
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, **kwargs):
        return self.describe_table(**kwargs)


class MSSQLController(BaseController):
    _connection = None
    _database = None
    _table = None
    _cursor = None

    def __init__(self, *args, **kwargs):
        super(MSSQLController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MSSQLController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    pass
                    # raise
                    print("Error getting the MSSQL attributes")
        elif not args and kwargs:
            try:
                host = kwargs.pop('host')
                port = kwargs.pop('port')
                user = kwargs.pop('connection_user')
                password = kwargs.pop('connection_password')
                self._database = kwargs.pop('database')
                self._table = kwargs.pop('table', None)
            except Exception as e:
                pass
                # raise
                print("Error getting the MSSQL attributes")
        try:
            self._connection = pymssql.connect(host=host, port=int(port), user=user, password=password,
                                               database=self._database)
            self._cursor = self._connection.cursor()
        except:
            self._connection = None
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    'select COLUMN_NAME, DATA_TYPE, IS_NULLABLE from information_schema.columns where table_name = %s',
                    (self._table,))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for
                        item in self._cursor]
            except:
                print('Error describing table: %s')
        return []

    def get_primary_keys(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1 AND TABLE_NAME = %s",
                    (self._table,))
                return [item[0] for item in self._cursor]
            except:
                print('Error ')
        return None

    def select_all(self, limit=50):
        if self._table is not None and self._database is not None and self._plug is not None:
            try:
                order_by = self._plug.plug_specification.all()[0].value
            except:
                order_by = None
            select = 'SELECT * FROM %s ' % self._table
            if order_by is not None:
                select += 'ORDER BY %s DESC ' % order_by
            if limit is not None and isinstance(limit, int):
                select += 'OFFSET 0 ROWS FETCH NEXT %s ROWS ONLY' % limit
            try:
                self._cursor.execute(select)
                cursor_select_all = [item for item in self._cursor]
                cursor_describe = self.describe_table()
                return [{column['name']: item[i] for i, column in enumerate(cursor_describe)} for item in
                        cursor_select_all]
            except Exception as e:
                print(e)
        return []

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        if plug is None:
            plug = self._plug
        data = self.select_all()
        id_list = self.get_primary_keys()
        parsed_data = [{'id': tuple(item[key] for key in id_list),
                        'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]}
                       for item in data]
        new_data = []
        for item in parsed_data:
            try:
                id_item = item['id'][0]
            except IndexError:
                id_item = None
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id_item)
            if not q.exists():
                for column in item['data']:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=id_item,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(parsed_data[0]['data'])
            extra = {'controller': 'mssql'}
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

    def _get_insert_statement(self, item):
        insert = """INSERT INTO %s (%s) VALUES (%s)""" % (
            self._table, """,""".join(item.keys()), """,""".join("""\'%s\'""" % i for i in item.values()))
        return insert

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
            extra = {'controller': 'mssql'}
            for item in data_list:
                try:
                    insert = self._get_insert_statement(item)
                    self._cursor.execute(insert)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (self._cursor.lastrowid), extra=extra)
                    obj_list.append(self._cursor.lastrowid)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (self._cursor.lastrowid), extra=extra)
            try:
                self._connection.commit()
            except:
                self._connection.rollback()
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, **kwargs):
        return self.describe_table(**kwargs)


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

    def get_target_fields(self, **kwargs):
        return self.get_module_fields(**kwargs)


class ControllerError(Exception):
    pass


def get_dict_with_source_data(source_data, target_fields, include_id=False):
    valid_map = OrderedDict()
    result = []
    for field in target_fields:
        if target_fields[field] != '':
            valid_map[field] = target_fields[field]
    for obj in source_data:
        user_dict = OrderedDict()
        for field in valid_map:
            kw = valid_map[field].split(' ')
            values = []
            for i, w in enumerate(kw):
                if w in ['%%%%%s%%%%' % k for k in obj['data'].keys()]:
                    values.append(obj['data'][w.replace('%', '')])
                else:
                    values.append(w)
            user_dict[field] = ' '.join(values)
        if include_id is True:
            user_dict['id'] = obj['id']
        result.append(user_dict)
    return result