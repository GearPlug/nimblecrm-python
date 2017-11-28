from collections import OrderedDict
import re
import xml.etree.ElementTree as ET
from importlib import import_module


def get_dict_with_source_data(source_data, target_fields, include_id=False):
    pattern = re.compile("(\%\%(.*?)+\%\%)")
    valid_map = OrderedDict()
    result = []
    for field in target_fields:
        if target_fields[field] != '':
            valid_map[field] = target_fields[field]
    for obj in source_data:
        user_dict = OrderedDict()
        for field in valid_map:
            w = html_decode(valid_map[field])
            res = pattern.findall(w)
            if res is not None and res:
                final_value = w
                for group in res:
                    data_key = re.sub("\%\%", "", group[0])
                    if data_key in obj['data']:
                        final_value = re.sub(re.escape(group[0]), obj['data'][data_key], final_value, 1)
            else:
                final_value = w
            user_dict[field] = final_value
        if "__filter__" in obj.keys():
            user_dict['__filter__'] = obj['__filter__']
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
