import copy
import random
import sugarcrm
from mailchimp3 import MailChimp
import re
import hashlib

import os
from oauth2client import tools
from oauth2client import client
import requests
import MySQLdb
import psycopg2
import pymssql


def try_mysql():
    host = '192.168.0.186'
    port = 3306
    user = 'faker'
    password = '123456'
    db = 'fakedata'
    a = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=db)
    print(a)
    a = "sudo celery -A apiconnector worker -l INFO --concurrency=10 -n worker1@%h"


class CustomSugarObject(sugarcrm.SugarObject):
    module = "CustomObject"

    def __init__(self, *args, **kwargs):
        if args:
            self.module = args[0]
        return super(CustomSugarObject, self).__init__(**kwargs)

    @property
    def query(self):
        return ''


def ej1():
    lista = []
    for i in range(1, 101):
        string = str(i)
        if i % 3 == 0 and i:
            string += "bazz"
        if i % 5 == 0:
            string += "buzz"
        lista.append(string)
    print(lista)


def ej2():
    lista = ['hola', 'chao', 'ayer', 'hoy', 'mirada', 'investigar', 'no', 'lista', 'bueno', 'ayer', 'a', 'contar']
    sorted_list = sorted(lista, key=lambda x: (len(x), x.lower()))
    print(sorted_list)


def ej3():
    lista_a = [random.randint(1, 50) for i in range(40)]
    lista_b = [random.randint(1, 50) for i in range(40)]
    lista_c = [i for i in lista_a if i not in lista_b]
    print(lista_a)
    print(lista_b)
    print(lista_c)


def try_sugar(url, user, password):
    session = sugarcrm.Session(url, user, password)
    print(session.session_id)
    lead = sugarcrm.Lead()
    s = session.get_entry_list(lead, max_results=30, order_by='date_entered DESC')
    print(len(s))
    for i in s:
        print(i.fields)


def try_mailchimp(user, password):
    client = MailChimp(user, password)
    # try:
    #     tt = client.list.all()
    #     print(tt)
    #     idp = '540db784d6'
    #     t = client.list._mc_client._get(url='lists/%s/merge-fields' % idp)
    # except Exception as e:
    #     print(e)
    #     t = None
    # for k in t['merge_fields']:
    #     for f in k:
    #         print('%s-> %s' % (f, k[f]))
    #     print('\n')
    # print(t is not None)

    # result = client.list.all()
    # lists = [{'name': l['name'], 'id': l['id']} for l in result['lists']]
    # print(lists)
    # email = 'lucas.doe@gmail.com'
    # m.update(email.encode())
    idp = '540db784d6'
    a = [{'email_address': 'jama.b@hotmail.com', 'merge_fields': {'LNAME': 'Bolivar Diaz', 'FNAME': 'Jacqueline Maria'},
          'status': 'subscribed'}]
    jhon = {
        'email_address': 'lucas.doe@gmail.com',
        'status': 'subscribed',
        'merge_fields': {
            'FNAME': 'John',
            'LNAME': 'Doe',
        },
    }
    result = client.member.create(idp, jhon)
    print(result)




    # result = client.member.create(idp, jhon)

    # result = client.member.get(idp, m.hexdigest())
    # print(result['status'])
    # if result['status'] == 404:
    #     print("Error")
    # else:
    #     print('%s %s %s' % (result['email_address'], '%s %s'%(result['merge_fields']['FNAME'],result['merge_fields']['LNAME']), result['id']))

    # result = client.member.update(idp, m.hexdigest(), {'status': 'unsubscribed'})
    # print(result)


def try_sub_dict(s, d):
    pattern = re.compile(r'\b(' + '|'.join(d.keys()) + r')\b')
    result = pattern.sub(lambda x: d[x.group()], s)
    print(result)


def try_google():
    flow = client.OAuth2WebServerFlow(
        client_id='292458000851-9q394cs5t0ekqpfsodm284ve6ifpd7fd.apps.googleusercontent.com',
        client_secret='eqcecSL7Ecp0hiMy84QFSzsD',
        scope='https://www.googleapis.com/auth/drive',
        redirect_uri='http://localhost/account/test/')
    auth_uri = flow.step1_get_authorize_url()
    print(auth_uri)


def try_postgres():
    host = 'localhost'
    port = 5432
    user = 'ingmferrer'
    password = '1234'
    db = 'test'
    table = 'test'
    conn = psycopg2.connect(host=host, port=int(port), user=user, password=password, database=db)
    cursor = conn.cursor()

    cursor.execute(
        'SELECT column_name, data_type, is_nullable FROM INFORMATION_SCHEMA.columns WHERE table_name = %s', (table,))
    describe = [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for
                item in cursor]

    print(describe)

    cursor.execute(
        'SELECT c.column_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name) JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema AND tc.table_name = c.table_name AND ccu.column_name = c.column_name where tc.table_name = %s',
        (table,))
    primary_key = [item[0] for item in cursor]

    print(primary_key)

    cursor.execute('SELECT * FROM %s' % table)
    select_all = [item for item in cursor]

    print(select_all)

    select_all_dict = [{column['name']: item[i] for i, column in enumerate(describe)} for item in select_all]

    print(select_all_dict)

    parsed_data = [{'id': tuple(item[key] for key in primary_key),
                    'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in primary_key]}
                   for item in select_all_dict]
    print(parsed_data)


def try_mssql():
    host = '181.143.188.178'
    database = 'testbd'
    table = 'client'
    port = '1489'
    user = 'test'
    password = '12345678'
    conn = pymssql.connect(host=host, user=user, password=password, database=database, port=port)
    cursor = conn.cursor()
    print(cursor)

    cursor.execute('select COLUMN_NAME, DATA_TYPE, IS_NULLABLE from information_schema.columns where table_name = %s', (table,))
    describe = [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for
                item in cursor]
    print(describe)

    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1 AND TABLE_NAME = %s", (table,))

    primary_key = [item[0] for item in cursor]

    print(primary_key)

    cursor.execute('SELECT * FROM %s' % table)
    select_all = [item for item in cursor]

    print(select_all)

    select_all_dict = [{column['name']: item[i] for i, column in enumerate(describe)} for item in select_all]

    print(select_all_dict)

    parsed_data = [{'id': tuple(item[key] for key in primary_key),
                    'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in primary_key]}
                   for item in select_all_dict]

    print(parsed_data)

# ej1()
# ej2()
# ej3()
# try_sugar('http://208.113.131.86/uat/uat/service/v4_1/rest.php', 'emarketing', 'zakaramk*')
# try_sub_dict('Hola soy german!', {'german': 'daniel'})
# try_mailchimp('MaxConceptLife63', '619813e972f8698c8029978a8dfc250d-us12')

# d = {'a':1, 'b':2, 'c':3}
# e = d
# d['a'] = 5
# print(d)
# print(e)
# try_google()
# try_mysql()
# try_postgres()
try_mssql()
