from faker import Factory
import pymysql
import time


class MySQLConnection(object):
    def __init__(self, host, port, user, passwd, db, table):
        self.host = host
        self.port = port
        self.user = user
        self.passwd = passwd
        self.db = db
        self.table = table


def generate_data(connection, amount=1):
    fake = Factory.create()
    db = pymysql.connect(host=connection.host,
                         user=connection.user,
                         passwd=connection.passwd,
                         db=connection.db,
                         autocommit=True)
    cursor = db.cursor()
    stuff = ["first_name", "last_name", "email", "bs", "ean", ]
    fields = ["dato1", "dato2", "dato3", "dato4", "dato5", "dato6", "dato7"]
    for n in range(amount):
        data = [fake.first_name(), fake.last_name(), fake.email(), fake.phone_number(), '', '', '']
        sql_fields = ','.join(["`{0}`".format(field) for field in fields])
        sustitution_fields = ','.join(["%s" for field in fields])
        sql = "INSERT INTO `{0}`.`{1}` ({2}) VALUES({3})".format(connection.db, connection.table, sql_fields,
                                                                 sustitution_fields)
        # print(sql)
        cursor.execute(sql, tuple(data))


connection_luisa = MySQLConnection('localhost', 3306, 'root', 'root', 'gr_test_1', 'luisa')
connection_nerio = MySQLConnection('localhost', 3306, 'root', 'root', 'gr_test_1', 'nerio')
connection_lelia = MySQLConnection('localhost', 3306, 'root', 'root', 'gr_test_1', 'lelia')
connection_jonathan = MySQLConnection('localhost', 3306, 'root', 'root', 'gr_test_1', 'jonathan')
auto_gen_number = 2
while True:
    generate_data(connection_luisa, auto_gen_number)
    generate_data(connection_nerio, auto_gen_number)
    generate_data(connection_lelia, auto_gen_number)
    generate_data(connection_jonathan, auto_gen_number)
    print("Data insertada: {0}".format(auto_gen_number))
    time.sleep(10)
