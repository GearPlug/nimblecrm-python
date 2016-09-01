import random


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


ej1()
ej2()
ej3()
