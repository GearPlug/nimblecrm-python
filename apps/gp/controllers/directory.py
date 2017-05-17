from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data, xml_to_dict
from apps.gp.models import StoredData

import json
import httplib2
import re
import requests
from xml.etree import ElementTree as ET
from oauth2client import client as GoogleClient


class GoogleContactsController(BaseController):
    _credential = None
    _token = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(GoogleContactsController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    credentials_json = self._connection_object.credentials_json
                except Exception as e:
                    print("Error getting the GoogleContacts attributes 1")
                    print(e)
                    credentials_json = None
        elif not args and kwargs:
            if 'credentials_json' in kwargs:
                credentials_json = kwargs.pop('credentials_json')
        else:
            credentials_json = None
        if credentials_json is not None:
            try:
                _json = json.dumps(credentials_json)
                self._credential = GoogleClient.OAuth2Credentials.from_json(_json)
                self.refresh_token()
                http_auth = self._credential.authorize(httplib2.Http())
                self._token = self._credential.get_access_token()
                # self._connection_obkect.credentials_json =
            except Exception as e:
                print("Error getting the GoogleSpreadSheets attributes 2")
                self._credential = None
                self._token = None
        return self._token is not None

    def _upate_connection_object_credentials(self):
        self._connection_object.credentials_json = self._credential.to_json()
        self._connection_object.save()

    def refresh_token(self, token=''):
        if self._credential.access_token_expired:
            self._credential.refresh(httplib2.Http())
            self._upate_connection_object_credentials()

    def get_creation_contact_fields(self):
        return ('name', 'surname', 'notes', 'email', 'display_name', 'email_home', 'phone_work', 'phone_home', 'city',
                'address', 'region', 'postal_code', 'country', 'formatted_address')

    def get_display_contact_fields(self):
        return ('title', 'notes', 'email', 'displayName', 'email_home', 'phoneNumber', 'phone_home', 'city',
                'address', 'region', 'postal_code', 'country', 'formatted_address')

    def get_contact_list(self, url="https://www.google.com/m8/feeds/contacts/default/full/"):
        r = requests.get(url, {'oauth_token': self._token.access_token, 'max-results': 100000, },
                         headers={'Content-Type': 'application/atom+xml', 'GData-Version': '3.0'})
        if r.status_code == 200:
            return xml_to_dict(r.text, iterator_string='{http://www.w3.org/2005/Atom}entry')
        return []

    def get_target_fields(self, **kwargs):
        return self.get_contact_fields(**kwargs)

    def send_stored_data(self, source_data, target_fields, is_first=False):
        print("Entre")
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        # print(data_list)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            extra = {'controller': 'google_contacts'}
            for obj in data_list:
                l = [val for val in obj.values()]
                obj_list.append(l)
        # print(obj_list)

        if self._plug is not None:
            for obj in data_list:
                l = [val for val in obj.values()]
                obj_list.append(l)
            extra = {'controller': 'google_spreadsheets'}
            sheet_values = self.get_worksheet_values()
            for idx, item in enumerate(obj_list, len(sheet_values) + 1):
                res = self.create_row(item, idx)
            return
        raise ControllerError("Incomplete.")

    def _create_contact_xml(self, dictionary):
        if 'email' not in dictionary and 'phone_work' not in dictionary and 'phone_home' not in dictionary:
            raise Exception("Error: es necesario el telefono o el email para crear un contacto.")

        root = ET.Element("atom:entry")
        root.attrib.update(
            {'xmlns:atom': 'http://www.w3.org/2005/Atom', 'xmlns:gd': 'http://schemas.google.com/g/2005'})
        category = ET.SubElement(root, "atom:category")
        category.attrib.update(
            {'scheme': 'http://schemas.google.com/g/2005#kind',
             'term': 'http://schemas.google.com/contact/2008#contact'})
        name = ET.SubElement(root, "gd:name")
        if 'name' in dictionary and dictionary['name']:
            xml_field_name = dictionary['name']
            given_name = ET.SubElement(name, "gd:givenName")
            given_name.text = dictionary['name']
        else:
            xml_field_name = ''
        if 'surname' in dictionary and dictionary['surname']:
            xml_field_surname = dictionary['surname']
            given_family_name = ET.SubElement(name, "gd:familyName")
            given_family_name.text = dictionary['surname']
        else:
            xml_field_surname = ''

        if xml_field_name or xml_field_surname:
            full_name = xml_field_name + " " + xml_field_surname
            given_full_name = ET.SubElement(name, "gd:fullName")
            given_full_name.text = full_name.strip()

        if 'email' in dictionary and dictionary['email']:
            email = ET.SubElement(root, "gd:email")
            email.attrib.update(
                {'rel': 'http://schemas.google.com/g/2005#work', 'primary': 'true', 'address': dictionary['email'], })
            if 'display_name' in dictionary and dictionary['display_name']:
                email.attrib.update({'displayName': dictionary['display_name'], })
            im = ET.SubElement(root, "gd:im")
            im.attrib.update(
                {'address': dictionary['email'], 'protocol': 'http://schemas.google.com/g/2005#GOOGLE_TALK',
                 'primary': 'true', 'rel': 'http://schemas.google.com/g/2005#home'})
        if 'email_home' in dictionary and dictionary['email_home']:
            email2 = ET.SubElement(root, "gd:email")
            email2.attrib.update({'rel': 'http://schemas.google.com/g/2005#home', 'address': dictionary['email_home']})
        if 'phone_work' in dictionary and dictionary['phone_work']:
            phonenumber = ET.SubElement(root, "gd:phoneNumber")
            phonenumber.attrib.update({'rel': 'http://schemas.google.com/g/2005#work', 'primary': 'true', })
            phonenumber.text = dictionary['phone_work']
        if 'phone_home' in dictionary and dictionary['phone_home']:
            phonehome = ET.SubElement(root, "gd:phoneNumber")
            phonehome.attrib.update({'rel': 'http://schemas.google.com/g/2005#home'})
            phonehome.text = dictionary['phone_home']

        structure = ET.SubElement(root, "gd:structuredPostalAddress")
        structure.attrib.update({'rel': 'http://schemas.google.com/g/2005#work', 'primary': 'true'})
        if 'city' in dictionary and dictionary['city']:
            city = ET.SubElement(structure, "gd:city")
            city.text = dictionary['city']
        if 'street' in dictionary and dictionary['street']:
            street = ET.SubElement(structure, "gd:street")
            street.text = dictionary['street']
        if 'region' in dictionary and dictionary['region']:
            region = ET.SubElement(structure, "gd:region")
            region.text = dictionary['region']
        if 'postal_code' in dictionary and dictionary['postal_code']:
            postal_code = ET.SubElement(structure, "gd:postcode")
            postal_code.text = dictionary['postal_code']
        if 'country' in dictionary and dictionary['country']:
            country = ET.SubElement(structure, "gd:country")
            country.text = dictionary['country']
        if 'formatted_address' in dictionary and dictionary['formatted_address']:
            formattedAddress = ET.SubElement(structure, "gd:formattedAddress")
            formattedAddress.text = dictionary['formatted_address']
        return ET.tostring(root).decode('utf-8')

    def create_contact(self, data):
        xml_sr = self._create_contact_xml(data)
        url = "https://www.google.com/m8/feeds/contacts/default/full/?oauth_token={0}".format(self._token.access_token)
        r = requests.post(url, data=xml_sr, headers={'Content-Type': 'application/atom+xml', 'GData-Version': '3.0'})
        return r.status_code == 201

        # print(r.text)
        # FALTA MENSAJE EXITOSO

    def download_to_stored_data(self, connection_object=None, plug=None, **kwargs):
        if connection_object is None:
            connection_object = self._connection_object
        if plug is None:
            plug = self._plug
        contact_list = self.get_contact_list()
        new_data = []
        for item in contact_list:
            id = None
            for tag in item['content']:
                if tag['tag'] == 'id':
                    id = tag['text']
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id)
            if not q.exists():
                for column in item['content']:
                    if column['tag'] not in ['link', 'id', 'category', 'updated', 'edited']:
                        sd_item = None
                        if column['tag'] in ['email', 'im']:
                            text = re.sub(u"[^\x20-\x7f]+", u"", column['attrib']['address']).strip() \
                                if column['attrib']['address'] is not None else ''
                            sd_item = StoredData(name=column['tag'], value=text, object_id=id,
                                                 connection=connection_object.connection, plug=plug)
                        elif column['tag'] in ['organization', 'name']:
                            sd_item = []
                            for column2 in column['content']:
                                text = re.sub(u"[^\x20-\x7f]+", u"", column2['text']).strip() \
                                    if column2['text'] is not None else ''
                                if column2['tag'] == 'orgName':
                                    sd_item.append(StoredData(name=column['tag'], value=text, object_id=id,
                                                              connection=connection_object.connection, plug=plug))
                                else:
                                    sd_item.append(StoredData(name=column2['tag'], value=text, object_id=id,
                                                              connection=connection_object.connection, plug=plug))
                        elif column['tag'] in ['extendedProperty']:
                            text = re.sub(u"[^\x20-\x7f]+", u"", column['attrib']['name']).strip() \
                                if column['attrib']['name'] is not None else ''
                            sd_item = StoredData(name=column['tag'], value=text, object_id=id,
                                                 connection=connection_object.connection, plug=plug)
                        elif column['tag'] in ['groupMembershipInfo']:
                            text = re.sub(u"[^\x20-\x7f]+", u"", column['attrib']['href']).strip() \
                                if column['attrib']['href'] is not None else ''
                            sd_item = StoredData(name=column['tag'], value=text, object_id=id,
                                                 connection=connection_object.connection, plug=plug)
                        else:
                            text = re.sub(u"[^\x20-\x7f]+", u"", column['text']).strip() \
                                if column['text'] is not None else ''
                            sd_item = StoredData(name=column['tag'], value=text, object_id=id,
                                                 connection=connection_object.connection, plug=plug)
                        if sd_item is not None:
                            if type(sd_item) == list:
                                new_data += sd_item
                            else:
                                new_data.append(sd_item)
        if new_data:
            extra = {'controller': 'googlecontacts'}
            last_id = None
            for contact_field in new_data:
                current_id = contact_field.id
                new_item = current_id != last_id
                try:
                    contact_field.save()
                    if new_item:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            current_id, item.plug.id, item.connection.id), extra=extra)
                except Exception as e:
                    print(contact_field.name, contact_field.value, e)
                    if new_item:
                        extra['status'] = 'f'
                        self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                            item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
                finally:
                    last_id = current_id
            return True
        return False

    def get_mapping_fields(self, ):
        return self.get_contact_fields()
