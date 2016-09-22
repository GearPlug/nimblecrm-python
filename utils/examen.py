import random
import sugarcrm
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
    custom_item = CustomSugarObject('Leads')
    modules = session.get_available_modules()
    # print(modules)
    # entries = session.get_entry_list(custom_item, )
    # print([e['name'] for e in entries[0].fields])
    fields = session.get_module_fields(custom_item, )
    # print(fields)
    # print(fields)
    # params = {'module': 'Leads', 'first_name': 'Esperanza', 'phone_mobile': '3145114385',
    #           'comentario_prospecto_c': 'Mucho dolor en el coxis y parte de la cadera derecha.',
    #           'last_name': 'Valencia Sanchez'}
    # params2 = {'last_name': 'prueba yonis name', 'phone_mobile': '5432'}
    # new_lead = CustomSugarObject('Leads', **params)
    # new_lead2 = CustomSugarObject('Leads', **params2)
    # a = session.set_entries([new_lead, ])


def try_sub_dict(s, d):
    pattern = re.compile(r'\b(' + '|'.join(d.keys()) + r')\b')
    result = pattern.sub(lambda x: d[x.group()], s)
    print(result)


# ej1()
# ej2()
# ej3()
try_sugar('http://208.113.131.86/uat/uat/service/v4_1/rest.php', 'emarketing', 'zakaramk*')
# try_sub_dict('Hola soy german!', {'german': 'daniel'})
