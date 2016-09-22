from django.shortcuts import render
import MySQLdb
import re


# Create your views here.

def api_prueba(request):
    connector_list = []
    contenido = "Prueba hola hola"
    ctx = {'contenido': contenido, 'connectorList': connector_list}
    return render(request, 'home/index.html', ctx)


def mysql_trigger_create_row(connection, target_data, values):
    # print(target_data)
    connection_reached = False
    name = connection.name
    host = connection.host
    port = connection.port
    database = connection.database
    user = connection.connection_user
    password = connection.connection_password
    table = connection.table
    print(target_data)
    print(values)
    try:
        conn = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=database)
    except:
        print("Error reaching the database")
    cursor = conn.cursor()
    insert = """INSERT INTO %s (%s) VALUES (%s)""" % (
        connection.table, """,""".join(target_data), ','.join(['%s' for i in target_data]))
    try:
        cursor.executemany(insert, values)
        conn.commit()
    except Exception as e:
        print("error")
        print(e)
        conn.rollback()
    # for item in cursor:
    #     print(item)
    return True


def mysql_get_insert_values(source_data, target_fields, *args, **kwargs):
    tag_list = ['%s' % target_fields[key] for key in target_fields]
    valid_target_data = [key for key in target_fields]
    d = [{attribute: {'%%%%%s%%%%' % a: item[attribute][a]
                      for a in item[attribute]} if attribute == 'data' else item[attribute] for attribute in item}
         for item in source_data]
    values = [tuple(item['data'][attribute] for attribute in item['data'] if attribute in tag_list) for item in d]
    column_order = ["%s" % valid_target_data[tag_list.index(attribute)].replace("%", "") for attribute in d[0]['data']
                    if attribute in tag_list]
    failed_data_list = []
    for v in values:
        if len(v) < len(column_order):
            failed_data_list.append(values.pop(values.index(v)))
    if failed_data_list:
        print("The next data failed to be delivered:")
        for i in failed_data_list:
            print(i)
    return column_order, values

    # sql_base_insert = 'INSERT INTO %s (%s) VALUES(%s)' % \
    #                   (sql_table_name, ','.join(sql_columns), ','.join(sql_insert_tags))
    # tag_list = ['%s' % target_data[key] for key in target_data]
    # regex = '(%s)' % '|'.join([re.escape(key) for key in tag_list])
    # regex_obj = re.compile(regex)
    # d = [{attribute: {'%%%%%s%%%%' % a: item[attribute][a]
    #                   for a in item[attribute]} if attribute == 'data' else item[attribute] for attribute in item}
    #      for item in source_data]
    # insert_list = []
    # for item in d:
    #     insert_list.append(regex_obj.sub(lambda x: item['data'][x.group()], sql_base_insert))
