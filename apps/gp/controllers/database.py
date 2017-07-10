from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data

from apps.gp.models import StoredData, ActionSpecification
import MySQLdb
import copy
import psycopg2
import pymssql


class MySQLController(BaseController):
    """
    MySQL Controller.

    """
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
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    print("Error getting the MySQL attributes args")
            if self._connection_object is None:
                raise ControllerError('No connection.')
            host = self._connection_object.host
            port = self._connection_object.port
            user = self._connection_object.connection_user
            password = self._connection_object.connection_password
            try:
                self._connection = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=self._database)
                self._cursor = self._connection.cursor()
            except Exception as e:
                self._connection = None

    def test_connection(self):
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute('DESCRIBE `%s`.`%s`' % (self._database, self._table))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2], 'is_primary': item[3] == 'PRI'} for
                        item in self._cursor]
            except:
                raise
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
            extra = {'controller': 'mysql'}
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
            extra = {'controller': 'mysql'}
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

    def get_mapping_fields(self, **kwargs):
        return [item['name'] for item in self.describe_table() if item['is_primary'] is not True]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'order by':
            return tuple({'id': c['name'], 'name': c['name']} for c in self.describe_table())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


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
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    print("Error getting the PostgreSQL attributes args")

    def test_connection(self):
        if self._connection_object is None:
            raise ControllerError('No connection.')
        host = self._connection_object.host
        port = self._connection_object.port
        user = self._connection_object.connection_user
        password = self._connection_object.connection_password
        try:
            self._connection = psycopg2.connect(host=host, port=int(port), user=user, password=password,
                                                database=self._database)
            self._cursor = self._connection.cursor()
        except Exception as e:
            self._connection = None
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    "SELECT column_name, data_type, is_nullable FROM INFORMATION_SCHEMA.columns WHERE table_schema= %s AND table_name = %s",
                    self._table.split('.'))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for
                        item in self._cursor]
            except:
                print('Error describing table: %s')
        return []

    def get_primary_keys(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    "SELECT c.column_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name) JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema AND tc.table_name = c.table_name AND ccu.column_name = c.column_name where c.table_schema = %s and tc.table_name = %s",
                    self._table.split('.'))
                return [item[0] for item in self._cursor]
            except Exception as e:
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

    def get_mapping_fields(self, **kwargs):
        return [item['name'] for item in self.describe_table() if item['name'] not in self.get_primary_keys()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'order by':
            return tuple({'id': c['name'], 'name': c['name']} for c in self.describe_table())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


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
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    pass
                    # raise
                    print("Error getting the MSSQL attributes")

    def test_connection(self):
        if self._connection_object is None:
            raise ControllerError('No connection.')
        host = self._connection_object.host
        port = self._connection_object.port
        user = self._connection_object.connection_user
        password = self._connection_object.connection_password
        try:
            self._connection = pymssql.connect(host=host, port=int(port), user=user, password=password,
                                               database=self._database)
            self._cursor = self._connection.cursor()
        except Exception as e:
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

    def get_mapping_fields(self, **kwargs):
        return [item['name'] for item in self.describe_table() if item['name'] not in self.get_primary_keys()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'order by':
            return tuple({'id': c['name'], 'name': c['name']} for c in self.describe_table())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")
