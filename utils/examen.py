import random
import sugarcrm
from mailchimp3 import MailChimp
import re


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
    result = client.list.all()
    lists = []
    for l in result['lists']:
        lists.append({'name': l['name'], 'id': l['id']})
    print(lists)
    jhon = {
        'email_address': 'lucas.doe@gmail.com',
        'status': 'subscribed',
        'merge_fields': {
            'FNAME': 'John',
            'LNAME': 'Doe',
        },
    }
    idp = '540db784d6'
    # result = client.member.create(idp, jhon)
    result = client.member.all(idp, email=jhon['email_address'], fields="members.email_address", get_all=True)
    for i in result['members']:
        print(i)
        # result = client.member.delete()


def try_sub_dict(s, d):
    pattern = re.compile(r'\b(' + '|'.join(d.keys()) + r')\b')
    result = pattern.sub(lambda x: d[x.group()], s)
    print(result)


# ej1()
# ej2()
# ej3()
# try_sugar('http://208.113.131.86/uat/uat/service/v4_1/rest.php', 'emarketing', 'zakaramk*')
# try_sub_dict('Hola soy german!', {'german': 'daniel'})
try_mailchimp('MaxConceptLife63', '619813e972f8698c8029978a8dfc250d-us12')
