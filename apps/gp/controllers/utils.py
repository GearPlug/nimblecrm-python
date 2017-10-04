from collections import OrderedDict
import re
import xml.etree.ElementTree as ET
from importlib import import_module


def get_dict_with_source_data(source_data, target_fields, include_id=False):
    pattern = re.compile("^(\%\%[\S+ ]+\%\%)$")
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
                w = html_decode(w)
                if w in ['%%{0}%%'.format(k) for k in obj['data'].keys()]:
                    values.append(obj['data'][w.replace('%%', '')])
                elif pattern.match(w):
                    values.append('')
                else:
                    values.append(w)
            user_dict[field] = ' '.join(values)
        if include_id is True:
            user_dict['id'] = obj['id']
        result.append(user_dict)
    return result


def xml_to_dict(xml, iterator_string=None):
    new_xml = ET.fromstring(xml)
    if iterator_string is not None:
        lista = new_xml.iter(iterator_string)
    else:
        lista = new_xml.iterall()
    return _recursive_xml_to_dict(lista)


def _recursive_xml_to_dict(lista):
    lista_dict = []
    # regex = re.compile('{(https?|ftp|http?)://(-\.)?([^\s/?\.#-]+\.?)+(/[^\s]*)?}(\S+)')
    regex = re.compile('^{(\S+)}(\S+)')
    for e in lista:
        result = regex.match(e.tag)
        if result is not None:  # and result.group(5) != 'link':
            dict_e = {'tag': result.group(2), 'attrib': e.attrib,
                      'text': e.text, 'content': _recursive_xml_to_dict(e)}
            lista_dict.append(dict_e)
    return lista_dict


def dynamic_import(name, path='', prefix='', suffix=""):
    mod = import_module(path)
    return getattr(mod, prefix + name + suffix)


def html_decode(s):
    """
    Returns the ASCII decoded version of the given HTML string. This does
    NOT remove normal HTML tags like <p>.
    """
    htmlCodes = (
        ("'", '&#39;'),
        ('"', '&quot;'),
        ('>', '&gt;'),
        ('<', '&lt;'),
        ('&', '&amp;')
    )
    for code in htmlCodes:
        s = s.replace(code[1], code[0])
    return s