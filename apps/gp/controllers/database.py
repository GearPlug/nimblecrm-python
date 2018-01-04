from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.models import StoredData, ActionSpecification
import copy
import MySQLdb
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

    def __init__(self, connection=None, plug=None, **kwargs):
        super(MySQLController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(MySQLController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._database = self._connection_object.database
                self._table = self._connection_object.table
                host = self._connection_object.host
                port = self._connection_object.port
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
            except AttributeError as e:
                raise ControllerError(code=1, controller=ConnectorEnum.MySQL.name,
                                      message='Error getting the MySQL attributes args. {}'.format(str(e)))
        else:
            raise ControllerError('No connection.')
        try:
            self._connection = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=self._database)
            self._cursor = self._connection.cursor()
        except MySQLdb.OperationalError as e:
            raise ControllerError(code=2, controller=ConnectorEnum.MySQL.name,
                                  message='Error instantiating the MySQL client. {}'.format(str(e)))

    def test_connection(self):
        try:
            self.describe_table()
            return True
        except Exception as e:
            print(e)
            return False

    def describe_table(self):
        try:
            self._cursor.execute('DESCRIBE `{0}`.`{1}`'.format(self._database, self._table))
            return [{'name': item[0], 'type': item[1], 'null': 'YES' == item, 'is_primary': item[3] == 'PRI',
                     'auto_increment': item[5] == 'auto_increment'} for item in self._cursor]
        except MySQLdb.OperationalError as e:
            raise ControllerError(code=2, controller=ConnectorEnum.MySQL.name,
                                  message='Error describing table. {}'.format(str(e)))
        except MySQLdb.ProgrammingError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.MySQL.name,
                                  message='Error describing table. {}'.format(str(e)))
        except Exception as e:
            raise ControllerError("Unexpected Exception. Please report this error: {}".format(str(e)))

    def select_all(self, limit=100, unique=None, order_by=None, gt=None):
        select = 'SELECT * FROM `{0}`.`{1}`'.format(self._database, self._table)
        if gt is not None:
            select += ' WHERE `{0}` > "{1}" '.format(order_by.value, gt)
        if unique is not None:
            select += 'GROUP BY `{0}` '.format(unique.value)
        if order_by is not None:
            select += 'ORDER BY `{0}` DESC '.format(order_by.value)
        if limit is not None and isinstance(limit, int):
            select += 'LIMIT {0}'.format(limit)
        try:
            self._cursor.execute(select)
            cursor_select_all = copy.copy(self._cursor)
            self.describe_table()
            return [{column[0]: item[i] for i, column in enumerate(self._cursor)} for item in cursor_select_all]
        except MySQLdb.OperationalError as e:
            raise ControllerError(code=2, controller=ConnectorEnum.MySQL.name,
                                  message='Error selecting all. {}'.format(str(e)))
        except MySQLdb.ProgrammingError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.MySQL.name,
                                  message='Error selecting all. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, limit=50, **kwargs):
        """
        :param connection_object:
        :param plug:
        :param last_source_record: IF the value is not None the download will ask for data after the value  recived.
        :param limit:
        :param kwargs:  ????  #TODO: CHECK
        :return:
        """
        order_by = self._plug.plug_action_specification.get(action_specification__name__iexact='order by')
        unique = self._plug.plug_action_specification.get(action_specification__name__iexact='unique')
        query_params = {'unique': unique, 'order_by': order_by, 'limit': limit}
        if last_source_record is not None:
            query_params['gt'] = last_source_record
        data = self.select_all(**query_params)
        new_data = []
        for item in data:
            unique_value = item[unique.value]
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=unique_value)
            if not q.exists():
                new_item = [StoredData(name=k, value=v or '', object_id=unique_value,
                                       connection=connection_object.connection, plug=plug) for k, v in item.items()]
                new_data.append(new_item)
        # Nueva forma
        obj_last_source_record = None
        result_list = []
        if new_data:
            # Revertir para enviar en el orden correcto.
            data.reverse()
            for item in reversed(new_data):  # Este es el for anterior y si, la lista se invierte tambien.
                obj_id = item[0].object_id
                obj_raw = "RAW DATA NOT FOUND."
                for i in data:  # Iter 'data' para buscar el 'dict' en 'data' del 'item' que iteramos en el for anterior
                    if i[unique.value] == obj_id:
                        obj_raw = i
                        break  # Paramos el for para que deje de iterar
                data.remove(i)  # Removemos 'i' de la lista 'data'
                is_stored, object_id = self._save_row(item)
                if object_id != obj_id:  # Validar que el 'obj_id' del stored data que se guardo es igual al id del item
                    print("ERROR NO ES EL MISMO ID:  {0} != 1}".format(object_id, obj_id))  # TODO: CHECK RAISE
                result_list.append({'identifier': {'name': unique.value, 'value': object_id},
                                    'raw': obj_raw, 'is_stored': is_stored, })
            for item in result_list:
                for k, v in item['raw'].items():  # Iter todos los campos que entraron
                    if k == order_by.value:
                        obj_last_source_record = v  # Sacamos el valor 'v' del key 'k' si k es el 'campo order_by'
                        break  # Paramos el for porque ya conseguimos lo que queriamos
                        # Se hace break proque el primer valor conseguido es que deberia ser utilizado
                        # porque la lista esta invertida
            return {'downloaded_data': result_list, 'last_source_record': obj_last_source_record}
        return False

    def _save_row(self, item):  # TODO: ASYNC METHOD
        try:
            for stored_data in item:
                stored_data.save()
            return True, stored_data.object_id
        except Exception as e:
            return False, item[0].object_id

    def _get_insert_statement(self, item):
        return """INSERT INTO `{0}`({1}) VALUES ({2})""".format(self._table, ",".join(item.keys()),
                                                                ",".join('\"{0}\"'.format(i) for i in item.values()))

    def send_stored_data(self, data_list):
        obj_list = []
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                insert = self._get_insert_statement(item)
                self._cursor.execute(insert)
                obj_result['response'] = "Succesfully inserted item with id {0}.".format(self._cursor.lastrowid)
                obj_result['sent'] = True
                obj_result['identifier'] = self._cursor.lastrowid
            except (UnicodeError, UnicodeDecodeError, UnicodeEncodeError, MySQLdb.ProgrammingError,
                    MySQLdb.OperationalError) as e:
                obj_result['response'] = "Failed to insert item. {}".format(e)
                obj_result['sent'] = False
                obj_result['identifier'] = '-1'
            obj_list.append(obj_result)
        try:
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            for obj in obj_list:
                obj['sent'] = False
                obj['identifier'] = '-1'
        return obj_list

    def get_target_fields(self, **kwargs):
        return self.describe_table(**kwargs)

    def get_mapping_fields(self):
        return [MapField(f, controller=ConnectorEnum.MySQL) for f in self.describe_table()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() in ['order by', 'unique']:
            return tuple({'id': c['name'], 'name': c['name']} for c in self.describe_table())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


class PostgreSQLController(BaseController):
    _connection = None
    _database = None
    _schema = None
    _table = None
    _cursor = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(PostgreSQLController, self).__init__(connection=connection,
                                                   plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(PostgreSQLController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._database = self._connection_object.database
                self._schema = self._connection_object.schema
                self._table = self._connection_object.table
                host = self._connection_object.host
                port = self._connection_object.port
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
            except Exception as e:
                raise ControllerError(code=1, controller=ConnectorEnum.PostgreSQL.name,
                                      message='Error getting the PostgreSQL attributes args. {}'.format(str(e)))
        else:
            raise ControllerError('No connection.')
        try:
            self._connection = psycopg2.connect(host=host, port=int(port), user=user, password=password,
                                                database=self._database)
            self._cursor = self._connection.cursor()
        except psycopg2.OperationalError as e:
            raise ControllerError(code=2, controller=ConnectorEnum.PostgreSQL.name,
                                  message='Error instantiating the PostgreSQL client. {}'.format(str(e)))

    def has_webhook(self):
        return None

    def test_connection(self):
        try:
            self.describe_table()
            return True
        except Exception as e:
            return False

    def has_webhook(self):
        return None

    def describe_table(self):
        try:
            self._cursor.execute(
                "SELECT column_name, data_type, is_nullable FROM INFORMATION_SCHEMA.columns WHERE table_schema= %s AND table_name = %s",
                (self._schema, self._table))
            return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for item in self._cursor]
        except psycopg2.OperationalError as e:
            raise ControllerError(code=2, controller=ConnectorEnum.PostgreSQL.name,
                                  message='Error describing table. {}'.format(str(e)))
        except psycopg2.ProgrammingError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.PostgreSQL.name,
                                  message='Error describing table. {}'.format(str(e)))
        except Exception as e:
            raise ControllerError("Unexpected Exception. Please report this error: {}".format(str(e)))

    def get_primary_keys(self):
        try:
            self._cursor.execute(
                "SELECT c.column_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name) JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema AND tc.table_name = c.table_name AND ccu.column_name = c.column_name where c.table_schema = %s and tc.table_name = %s",
                (self._schema, self._table))
            return [item[0] for item in self._cursor]
        except Exception as e:
            raise ControllerError("Unexpected Exception. Please report this error: {}".format(str(e)))

    def select_all(self, limit=100, unique=None, order_by=None, gt=None):
        select = 'SELECT * FROM {0}.{1}.{2}'.format(
            self._database, self._schema, self._table)
        if gt is not None:
            select += ' WHERE {0} > \'{1}\''.format(order_by.value, gt)
        if unique is not None:
            select += ' GROUP BY {0}'.format(unique.value)
        if order_by is not None:
            select += ' ORDER BY {0} DESC'.format(order_by.value)
        if limit is not None and isinstance(limit, int):
            select += ' LIMIT {0}'.format(limit)
        try:
            self._cursor.execute(select)
            cursor_select_all = [item for item in self._cursor]
            cursor_describe = self.describe_table()
            return [{column['name']: item[i] for i, column in enumerate(cursor_describe)} for item in cursor_select_all]
        except psycopg2.OperationalError as e:
            raise ControllerError(code=2, controller=ConnectorEnum.PostgreSQL.name,
                                  message='Error describing table. {}'.format(str(e)))
        except psycopg2.ProgrammingError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.PostgreSQL.name,
                                  message='Error describing table. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, limit=50, **kwargs):
        order_by = self._plug.plug_action_specification.get(action_specification__name__iexact='order by')
        unique = self._plug.plug_action_specification.get(action_specification__name__iexact='unique')
        query_params = {'unique': unique, 'order_by': order_by, 'limit': limit}
        if last_source_record is not None:
            query_params['gt'] = last_source_record
        data = self.select_all(**query_params)

        new_data = []
        for item in data:
            unique_value = item[unique.value]
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=unique_value)
            if not q.exists():
                new_item = [StoredData(name=k, value=v or '', object_id=unique_value, plug=plug,
                                       connection=connection_object.connection) for k, v in item.items()]
                new_data.append(new_item)
        obj_last_source_record = None
        result_list = []
        if new_data:
            data.reverse()
            for item in reversed(new_data):
                obj_id = item[0].object_id
                obj_raw = "RAW DATA NOT FOUND."
                for i in data:
                    if i[unique.value] == obj_id:
                        obj_raw = i
                        break
                data.remove(i)
                is_stored, object_id = self._save_row(item)
                if object_id != obj_id:
                    print("ERROR NO ES EL MISMO ID:  {0} != 1}".format(object_id, obj_id))  # TODO: CHECK RAISE
                result_list.append({'identifier': {'name': unique.value, 'value': object_id},
                                    'raw': obj_raw, 'is_stored': is_stored, })
            for item in result_list:
                for k, v in item['raw'].items():
                    if k == order_by.value:
                        obj_last_source_record = v
                        break
            return {'downloaded_data': result_list, 'last_source_record': obj_last_source_record}
        return False

    def _save_row(self, item):  # TODO: ASYNC METHOD
        try:
            for stored_data in item:
                stored_data.save()
            return True, stored_data.object_id
        except Exception as e:
            return False, item[0].object_id

    def _get_insert_statement(self, item):
        return """INSERT INTO {0}.{1} ({2}) VALUES ({3}) RETURNING id""".format(
            self._schema, self._table, ",".join(item.keys()),
            ",".join('\'{0}\''.format(i) for i in item.values()))

    def send_stored_data(self, data_list):
        obj_list = []
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                insert = self._get_insert_statement(item)
                self._cursor.execute(insert)
                fetch = self._cursor.fetchone()[0]
                obj_result['response'] = "Succesfully inserted item with id {0}.".format(fetch)
                obj_result['sent'] = True
                obj_result['identifier'] = fetch
            except psycopg2.ProgrammingError:  # TODO REVISAR
                obj_result['response'] = "Se envio el objeto pero no existe resultado.."
                obj_result['sent'] = True
                obj_result['identifier'] = "-1"
            except Exception as e:
                obj_result['response'] = "Failed to insert item ."
                obj_result['sent'] = False
                obj_result['identifier'] = "-1"
            obj_list.append(obj_result)
        try:
            self._connection.commit()
        except:
            self._connection.rollback()
            for obj in obj_list:
                obj['sent'] = False
                obj['identifier'] = '-1'
        return obj_list

    def get_mapping_fields(self, **kwargs):
        return [MapField(f, controller=ConnectorEnum.PostgreSQL) for f in self.describe_table()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() in ['order by', 'unique']:
            return tuple({'id': c['name'], 'name': c['name']} for c in
                         self.describe_table())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def get_target_fields(self, **kwargs):
        return self.describe_table(**kwargs)


class MSSQLController(BaseController):
    _connection = None
    _database = None
    _table = None
    _cursor = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(MSSQLController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(MSSQLController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._database = self._connection_object.database
                self._table = self._connection_object.table
                host = self._connection_object.host
                port = self._connection_object.port
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
            except Exception as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.MSSQL.name,
                                      message='The attributes necessary to make the connection were not obtained {}'.format(
                                          str(e)))
        else:
            raise ControllerError(code=1002, controller=ConnectorEnum.MSSQL.name,
                                  message='The controller is not instantiated correctly.')
        try:
            self._connection = pymssql.connect(host=host, port=int(port), user=user, password=password,
                                               database=self._database)
            self._cursor = self._connection.cursor()
        except Exception as e:
            raise ControllerError(code=1003, controller=ConnectorEnum.MSSQL.name,
                                  message='Error in the instantiation of the client.. {}'.format(str(e)))

    def test_connection(self):
        try:
            self.describe_table()
            return True
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.MSSQL.name,
            # message='Error in the connection test... {}'.format(str(e)))
            return False

    @property
    def has_webhook(self):
        return False

    @property
    def needs_polling(self):
        return True

    def describe_table(self):
        try:
            self._cursor.execute(
                'select COLUMN_NAME, DATA_TYPE, IS_NULLABLE from information_schema.columns where table_name = %s',
                (self._table,))
            return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for item in self._cursor]
        except Exception as e:
            raise ControllerError("Unexpected Exception. Please report this error: {}".format(str(e)))

    def get_primary_keys(self):
        try:
            self._cursor.execute(
                "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1 AND TABLE_NAME = %s",
                (self._table,))
            return [item[0] for item in self._cursor]
        except Exception as e:
            raise ControllerError("Unexpected Exception. Please report this error: {}".format(str(e)))

    def select_all(self, limit=50, unique=None, order_by=None, gt=None):
        try:
            cursor_describe = self.describe_table()
            describe = [f['name'] for f in cursor_describe]
        except Exception as e:
            raise ControllerError(code=2, controller=ConnectorEnum.MSSQL.name,
                                  message='Error describing table. {}'.format(str(e)))

        columns = ', '.join(
            map(lambda x: 'MAX({})'.format(x) if x != unique.value else 'DISTINCT ({})'.format(x), describe))
        select = 'SELECT {0} FROM {1}'.format(columns, self._table)
        if gt is not None:
            select += ' WHERE {0} > \'{1}\''.format(order_by.value, gt)
        if unique is not None:
            select += ' GROUP BY {0}'.format(unique.value)
        if order_by is not None:
            select += ' ORDER BY {0} DESC'.format(order_by.value)
        if limit is not None and isinstance(limit, int):
            select += ' OFFSET 0 ROWS FETCH NEXT %s ROWS ONLY' % limit

        try:
            self._cursor.execute(select)
            cursor_select_all = [item for item in self._cursor]
            cursor_describe = self.describe_table()
            return [{column['name']: item[i] for i, column in enumerate(cursor_describe)} for item in cursor_select_all]
        except Exception as e:
            raise ControllerError(code=2, controller=ConnectorEnum.MSSQL.name,
                                  message='Error describing table. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, limit=50, **kwargs):
        order_by = self._plug.plug_action_specification.get(action_specification__name__iexact='order by')
        unique = self._plug.plug_action_specification.get(action_specification__name__iexact='unique')
        query_params = {'unique': unique, 'order_by': order_by, 'limit': limit}
        if last_source_record is not None:
            query_params['gt'] = last_source_record
        data = self.select_all(**query_params)

        new_data = []
        for item in data:
            unique_value = item[unique.value]
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=unique_value)
            if not q.exists():
                new_item = [StoredData(name=k, value=v or '', object_id=unique_value,
                                       connection=connection_object.connection, plug=plug) for k, v in item.items()]
                new_data.append(new_item)

        obj_last_source_record = None
        result_list = []
        if new_data:
            data.reverse()
            for item in reversed(new_data):
                obj_id = item[0].object_id
                obj_raw = "RAW DATA NOT FOUND."
                for i in data:
                    if i[unique.value] == obj_id:
                        obj_raw = i
                        break
                data.remove(i)
                is_stored, object_id = self._save_row(item)
                if object_id != obj_id:
                    print("ERROR NO ES EL MISMO ID:  {0} != 1}".format(object_id, obj_id))  # TODO: CHECK RAISE
                result_list.append({'identifier': {'name': unique.value, 'value': object_id},
                                    'raw': obj_raw, 'is_stored': is_stored, })
            for item in result_list:
                for k, v in item['raw'].items():
                    if k == order_by.value:
                        obj_last_source_record = v
                        break
            return {'downloaded_data': result_list, 'last_source_record': obj_last_source_record}
        return False

    def _save_row(self, item):  # TODO: ASYNC METHOD
        try:
            for stored_data in item:
                stored_data.save()
            return True, stored_data.object_id
        except Exception as e:
            return False, item[0].object_id

    def _get_insert_statement(self, item):
        return """INSERT INTO %s (%s) VALUES (%s)""" % (
            self._table, """,""".join(item.keys()), """,""".join("""\'%s\'""" % i for i in item.values()))

    def send_stored_data(self, data_list):
        obj_list = []
        for item in data_list:
            obj_result = {'data': dict(item)}
            try:
                insert = self._get_insert_statement(item)
                self._cursor.execute(insert)
                fetch = self._cursor.lastrowid
                obj_result['response'] = "Succesfully inserted item with id {0}.".format(fetch)
                obj_result['sent'] = True
                obj_result['identifier'] = fetch
            except Exception as e:
                obj_result['response'] = "Failed to insert item ."
                obj_result['sent'] = False
                obj_result['identifier'] = "-1"
            obj_list.append(obj_result)
        try:
            self._connection.commit()
        except:
            self._connection.rollback()
            for obj in obj_list:
                obj['sent'] = False
                obj['identifier'] = '-1'
        return obj_list

    def get_mapping_fields(self, **kwargs):
        return [MapField(item, controller=ConnectorEnum.MSSQL) for item in self.describe_table()]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() in ['order by', 'unique']:
            return tuple({'id': c['name'], 'name': c['name']} for c in self.describe_table())
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")
