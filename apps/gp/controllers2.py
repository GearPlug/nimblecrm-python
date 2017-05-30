from apps.gp.models import StoredData, PlugSpecification, GooglePushWebhook
from apiconnector.settings import FACEBOOK_APP_SECRET, FACEBOOK_APP_ID, FACEBOOK_GRAPH_VERSION, GOOGLE_CLIEN_ID, \
    GOOGLE_CLIENT_SECRET
from apiconnector.settings import FACEBOOK_APP_SECRET, FACEBOOK_APP_ID, FACEBOOK_GRAPH_VERSION
from django.conf import settings
import tweepy
import surveymonty
import facebook
import json
import requests
import hmac
import hashlib
import logging
import MySQLdb
import psycopg2
import pymssql
import copy
import sugarcrm
import time
import uuid
from apiclient import discovery
from mailchimp3 import MailChimp
from oauth2client import client as GoogleClient
from getresponse.client import GetResponse
import httplib2
from collections import OrderedDict
from slacker import Slacker
import re
from bitbucket.bitbucket import Bitbucket
import simplejson as json
from jira import JIRA
from base64 import b64encode
import xml.etree.ElementTree as ET

logger = logging.getLogger('controller')


class BaseController(object):
    """
    Abstract controller class.
    - The init calls the create_connection method.

    """
    _connection_object = None
    _plug = None
    _log = logging.getLogger('controller')

    def __init__(self, *args, **kwargs):
        self.create_connection(*args, **kwargs)

    def create_connection(self, *args):
        if args:
            self._connection_object = args[0]
            try:
                self._plug = args[1]
            except:
                pass
            return

    def send_stored_data(self, *args, **kwargs):
        raise ControllerError('Not implemented yet.')

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        raise ControllerError('Not implemented yet.')

    def download_source_data(self, **kwargs):
        if self._connection_object is not None and self._plug is not None:
            return self.download_to_stored_data(self._connection_object, self._plug, **kwargs)
        else:
            raise ControllerError("There's no active connection or plug.")

    def get_target_fields(self, **kwargs):
        raise ControllerError("Not implemented yet.")

    def get_mapping_fields(self, **kwargs):
        raise ControllerError("Not implemented yet.")


class SlackController(BaseController):
    _token = None
    _slacker = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(SlackController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._slacker = Slacker(self._token)
                except Exception as e:
                    print("Error getting the Slack Token")
                    print(e)
        elif kwargs:
            print(kwargs)
        return self._token is not None and self._slacker is not None

    def get_channel_list(self):
        response = self._slacker.channels.list()
        if 'successful' in response.__dict__ and response.__dict__['successful'] == True:
            data = json.loads(response.__dict__['raw'])
            channel_list = tuple({'id': c['id'], 'name': c['name']} for c in data['channels'])
            print(channel_list)
            return channel_list

        else:
            return []
            # raise ("Not implemented yet.")

    def post_message_to_target(self, message='', target=''):
        try:
            self._slacker.chat.post_message(target, message)
            return True
        except Exception as e:
            raise
            return False

    def post_message_to_channel(self, message=None, channel=None):
        if message is not None and channel is not None:
            self.post_message_to_target(message=message, target=channel)
        else:
            print("Error: debes enviar message y channel.")
            return False

    def post_message_to_user(self, message=None, user=None):
        if message is not None and user is not None:
            self.post_message_to_target(message=message, target=user)
        else:
            print("Error: debes enviar message y user.")
            return False

    def get_target_fields(self, **kwargs):
        return ['message']

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            extra = {'controller': 'slack'}
            for specification in self._plug.plug_specification.all():
                try:
                    target = PlugSpecification.objects.get(plug=self._plug,
                                                           action_specification=specification.action_specification)
                except Exception as e:
                    raise
            for obj in data_list:
                l = [val for val in obj.values()]
                obj_list.append(l)
            for o in obj_list:
                res = self.post_message_to_target(o, target.value)
            return
        raise ControllerError("Incomplete.")

    def download_to_stored_data(self, connection_object=None, plug=None, event=None, **kwargs):
        if event is not None:
            new_message = None
            if 'type' in event and event['event']['type'] == 'message':
                print(event['event_id'], event['event_time'], event['event']['text'])
                q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                              object_id=event['event_id'])
                if not q.exists():
                    new_message = StoredData(connection=connection_object.connection, plug=plug,
                                             object_id=event['event_id'], name=event['event']['type'],
                                             value=event['event']['text'])
                extra = {}
                if new_message is not None:
                    extra['status'] = 's'
                    extra = {'controller': 'google_spreadsheets'}
                    self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                        new_message.object_id, new_message.plug.id, new_message.connection.id), extra=extra)
                    new_message.save()
        return False


class GoogleCalendarController(BaseController):
    _connection = None
    _credential = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(GoogleCalendarController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    credentials_json = self._connection_object.credentials_json
                except Exception as e:
                    print("Error getting the GoogleCalendar attributes 1")
                    print(e)
                    credentials_json = None
        elif not args and kwargs:
            if 'credentials_json' in kwargs:
                credentials_json = kwargs.pop('credentials_json')
        else:
            credentials_json = None
        calendars = None
        if credentials_json is not None:
            try:
                _json = json.dumps(credentials_json)
                self._credential = GoogleClient.OAuth2Credentials.from_json(_json)
                http_auth = self._credential.authorize(httplib2.Http())
                service = discovery.build('calendar', 'v3', http=http_auth)
                calendar_list = service.calendarList().list().execute()
                calendars = calendar_list['items']
            except Exception as e:
                print("Error getting the GoogleCalendar attributes 2")
                self._credential = None
                calendars = None
        return calendars is not None

    def download_to_stored_data(self, connection_object=None, plug=None, events=None, **kwargs):
        if events is not None:
            _items = []
            for event in events:
                q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                              object_id=event['id'])
                if not q.exists():
                    for k, v in event.items():
                        obj = StoredData(connection=connection_object.connection, plug=plug,
                                         object_id=event['id'], name=k, value=v or '')
                        _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'googlecalendar'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def get_calendar_list(self):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http_auth)
        calendar_list = service.calendarList().list().execute()
        _list = []
        for c in calendar_list['items']:
            c['name'] = c['summary']
            _list.append(c)
        calendars = tuple(c for c in _list)
        return calendars

    def create_webhook(self):
        url = 'https://www.googleapis.com/calendar/v3/calendars/{}/events/watch'.format(
            self._plug.plug_specification.all()[0].value)

        headers = {
            'Authorization': 'Bearer {}'.format(self._connection_object.credentials_json['access_token']),
            'Content-Type': 'application/json'
        }

        body = {
            "id": str(uuid.uuid4()),
            "type": "web_hook",
            "address": "https://m.grplug.com/wizard/google/calendar/webhook/event/"
        }

        r = requests.post(url, headers=headers, json=body)
        if r.status_code == 200:
            data = r.json()
            GooglePushWebhook.objects.create(connection=self._connection_object.connection, channel_id=data['id'],
                                             resource_id=data['resourceId'], expiration=data['expiration'])
            return True
        return False

    def get_events(self):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http_auth)
        eventsResult = service.events().list(
            calendarId='primary', maxResults=10, singleEvents=True,
            orderBy='startTime').execute()
        return eventsResult.get('items', None)


class JiraController(BaseController):
    _connection = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(JiraController, self).create_connection(*args)
            if self._connection_object is not None:
                host = self._connection_object.host
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
        elif kwargs:
            host = kwargs.pop('host', None)
            user = kwargs.pop('connection_user', None)
            password = kwargs.pop('connection_password', None)
        else:
            host, user, password = None, None, None
        if host and user and password:
            try:
                self._connection = JIRA(host, basic_auth=(user, password))
            except Exception as e:
                print("Error getting the Jira attributes")
                print(e)
                self._connection = None
        return self._connection is not None

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            for obj in data_list:
                res = self.create_issue(self._plug.plug_specification.all()[0].value, obj)
            extra = {'controller': 'jira'}
            return
        raise ControllerError("Incomplete.")

    def download_to_stored_data(self, connection_object=None, plug=None, issue=None, **kwargs):
        if issue is not None:
            issue_key = issue['key']
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=issue_key)
            if not q.exists():
                for k, v in issue['fields'].items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=issue_key, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'jira'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def get_projects(self):
        return self._connection.projects()

    def create_issue(self, project_id, fields):
        if 'reporter' in fields:
            reporter_name = fields['reporter']
            fields['reporter'] = {'name': reporter_name}
        if 'assignee' in fields:
            assignee_name = fields['assignee']
            fields['assignee'] = {'name': assignee_name}
        if 'issuetype' in fields:
            issue_type = fields['issuetype']
            fields['issuetype'] = {'id': issue_type}
        if 'priority' in fields:
            priority = fields['priority']
            fields['priority'] = {'id': priority}
        fields['project'] = project_id
        return self._connection.create_issue(event=fields)

    def create_webhook(self):
        url = '{}/rest/webhooks/1.0/webhook'.format(self._connection_object.host)
        key = self.get_key(self._plug.plug_specification.all()[0].value)
        body = {
            "name": "Gearplug Webhook",
            "url": "http://grplug.com/wizard/jira/webhook/event/",
            "events": [
                "jira:issue_created",
            ],
            "jqlFilter": "Project={}".format(key),
            "excludeIssueDetails": False
        }
        r = requests.post(url, headers=self._get_header(), json=body)
        if r.status_code == 201:
            return True
        return False

    def get_key(self, project_id):
        for project in self.get_projects():
            if project.id == project_id:
                return project.key
        return None

    def _get_header(self):
        authorization = '{}:{}'.format(self._connection_object.connection_user,
                                       self._connection_object.connection_password)
        return {'Accept': 'application/json',
                'Authorization': 'Basic {0}'.format(b64encode(authorization.encode('UTF-8')).decode('UTF-8'))}

    def get_users(self):
        payload = {
            'project': self.get_key(self._plug.plug_specification.all()[0].value)
        }

        url = 'http://jira.grplug.com:8080/rest/api/2/user/assignable/search'
        r = requests.get(url, headers=self._get_header(), params=payload)
        if r.status_code == requests.codes.ok:
            return [{'id': u['name'], 'name': u['displayName']} for u in r.json()]
        return []

    def get_meta(self):
        meta = self._connection.createmeta(projectIds=self._plug.plug_specification.all()[0].value,
                                           issuetypeNames='Task', expand='projects.issuetypes.fields')
        exclude = ['attachment', 'project']

        users = self.get_users()

        def f(d, v):
            d.update({'id': v})
            return d

        _dict = [f(v, k) for k, v in meta['projects'][0]['issuetypes'][0]['fields'].items() if
                 k not in exclude]

        for d in _dict:
            if d['id'] == 'reporter' or d['id'] == 'assignee':
                d['allowedValues'] = users

        return sorted(_dict, key=lambda i: i['name'])

    def get_target_fields(self, **kwargs):
        return self.get_meta(**kwargs)


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


class TwitterController(BaseController):
    _token = None
    _token_secret = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(TwitterController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._token_secret = self._connection_object.token_secret
                except Exception as e:
                    print("Error getting the Twitter Token")
                    print(e)
        elif kwargs:
            if 'token' in kwargs and 'token_secret' in kwargs:
                self._token = kwargs['token']
                self._token_secret = kwargs['token_secret']
        me = None
        if self._token and self._token_secret:
            api = tweepy.API(self.get_twitter_auth())
            me = api.me()
        return me is not None

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            for obj in data_list:
                self.post_tweet(obj)
            extra = {'controller': 'twitter'}
        raise ControllerError("Incomplete.")

    def get_twitter_auth(self):
        consumer_key = settings.TWITTER_CLIENT_ID
        consumer_secret = settings.TWITTER_CLIENT_SECRET
        auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        auth.set_access_token(self._token, self._token_secret)
        return auth

    def post_tweet(self, item):
        api = tweepy.API(self.get_twitter_auth())
        api.update_status(**item)

    def get_target_fields(self, **kwargs):
        return [{
            'name': 'status',
            'required': True,
            'type': 'text',
        }, {
            'name': 'in_reply_to_status_id',
            'required': False,
            'type': 'text',
        }, {
            'name': 'lat',
            'required': False,
            'type': 'text',
        }, {
            'name': 'long',
            'required': False,
            'type': 'text',
        }, {
            'name': 'place_id',
            'required': False,
            'type': 'text',
        }]


class GoogleSpreadSheetsController(BaseController):
    _credential = None
    _spreadsheet_id = None
    _worksheet_name = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(GoogleSpreadSheetsController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    credentials_json = self._connection_object.credentials_json
                except Exception as e:
                    print("Error getting the GoogleSpreadSheets attributes 1")
                    print(e)
                    credentials_json = None
        elif not args and kwargs:
            if 'credentials_json' in kwargs:
                credentials_json = kwargs.pop('credentials_json')
        else:
            credentials_json = None
        files = None
        if credentials_json is not None:
            try:
                for s in self._plug.plug_specification.all():
                    if s.action_specification.name.lower() == 'spreadsheet':
                        self._spreadsheet_id = s.value
                    if s.action_specification.name.lower() == 'worksheet':
                        self._worksheet_name = s.value
            except:
                print("Error asignando los specifications 1")
            try:
                _json = json.dumps(credentials_json)
                self._credential = GoogleClient.OAuth2Credentials.from_json(_json)
                self._refresh_token()
                http_auth = self._credential.authorize(httplib2.Http())
                drive_service = discovery.build('drive', 'v3', http=http_auth)
                files = drive_service.files().list().execute()
            except Exception as e:
                print("Error getting the GoogleSpreadSheets attributes 2")
                self._credential = None
                files = None
        return files is not None

    def _upate_connection_object_credentials(self):
        self._connection_object.credentials_json = self._credential.to_json()
        self._connection_object.save()

    def _refresh_token(self, token=''):
        if self._credential.access_token_expired:
            self._credential.refresh(httplib2.Http())
            self._upate_connection_object_credentials()

    def download_to_stored_data(self, connection_object, plug, *args, **kwargs):
        if plug is None:
            plug = self._plug
        if not self._spreadsheet_id or not self._worksheet_name:
            return False
        sheet_values = self.get_worksheet_values()
        new_data = []
        for idx, item in enumerate(sheet_values[1:]):
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=idx + 1)
            if not q.exists():
                for idx2, cell in enumerate(item):
                    new_data.append(StoredData(name=sheet_values[0][idx2], value=cell, object_id=idx + 1,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(sheet_values)
            extra = {'controller': 'google_spreadsheets'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            # raise IndexError("hola")
            return True
        return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
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

    def colnum_string(self, n):
        div = n
        string = ""
        temp = 0
        while div > 0:
            module = (div - 1) % 26
            string = chr(65 + module) + string
            div = int((div - module) / 26)
        return string

    def get_sheet_list(self):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        drive_service = discovery.build('drive', 'v3', http=http_auth)
        files = drive_service.files().list().execute()
        sheet_list = tuple(
            f for f in files['files'] if 'mimeType' in f and f['mimeType'] == 'application/vnd.google-apps.spreadsheet')
        return sheet_list

    def get_worksheet_list(self, sheet_id):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        result = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        worksheet_list = tuple(i['properties'] for i in result['sheets'])
        return worksheet_list

    def get_worksheet_values(self, from_row=None, limit=None):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        res = sheets_service.spreadsheets().values().get(spreadsheetId=self._spreadsheet_id,
                                                         range='{0}'.format(self._worksheet_name)).execute()
        values = res['values']
        if from_row is None and limit is None:
            return values
        else:
            limit = limit if limit is not None else len(values) - 1
            from_row = from_row - 1 if from_row is not None else 0
            return values[from_row:from_row + limit]
        return values

    def get_worksheet_first_row(self):
        return self.get_worksheet_values(from_row=1, limit=1)[0]

    def get_worksheet_second_row(self):
        return self.get_worksheet_values(from_row=2, limit=1)[0]

    def create_row(self, row, idx):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())

        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        body = {
            'values': [row]
        }
        _range = "{0}!A{1}:{2}{1}".format(self._worksheet_name, idx, self.colnum_string(len(row)))
        res = sheets_service.spreadsheets().values().update(
            spreadsheetId=self._spreadsheet_id,
            range=_range, valueInputOption='RAW',
            body=body).execute()

        return res

    def get_target_fields(self, **kwargs):
        return self.get_worksheet_first_row(**kwargs)


class GetResponseController(BaseController):
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(GetResponseController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._client = GetResponse(self._connection_object.api_key)
                except Exception as e:
                    print("Error getting the GetResponse attributes")
                    self._client = None
        elif not args and kwargs:
            if 'api_key' in kwargs:
                api_key = kwargs.pop('api_key')
            try:
                self._client = GetResponse(api_key)
                print("%s %s", (api_key))
                print(self._client)
            except Exception as e:
                print(e)
                print("Error getting the GetResponse attributes")
                self._client = None
        t = self.get_campaigns()
        return t is not None

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            status = None
            for specification in self._plug.plug_specification.all():
                if specification.action_specification.action.name == 'subscribe':
                    status = 'subscribed'
                elif specification.action_specification.action.name == 'unsubscribe':
                    status = 'unsubscribed'
            extra = {'controller': 'getresponse'}
            for obj in data_list:
                if status == 'subscribed':
                    res = self.subscribe_contact(self._plug.plug_specification.all()[0].value, obj)
                else:
                    res = self.unsubscribe_contact(obj)
            return
        raise ControllerError("Incomplete.")

    def subscribe_contact(self, campaign_id, obj):
        _dict = {
            "email": obj.pop('email'),
            "campaign": {"campaignId": campaign_id}
        }
        if 'name' in obj:
            _dict['name'] = obj.pop('name')
        if 'dayOfCycle' in obj:
            _dict['dayOfCycle'] = obj.pop('dayOfCycle')
        if 'ipAddress' in obj:
            _dict['ipAddress'] = obj.pop('ipAddress')
        if obj:
            _dict["customFieldValues"] = [{"customFieldId": k, "value": [v]} for k, v in obj.items()]
        self._client.create_contact(_dict)

    def unsubscribe_contact(self, obj):
        self._client.delete_contact(obj.pop('id'))

    def get_campaigns(self):
        if self._client:
            result = self._client.get_campaigns({'sort': {'name', 'desc'}})
            try:
                return [{'name': l.name, 'id': l.id} for l in result]
            except:
                return []
        return []

    def get_meta(self):
        _list = [{
            'name': 'name',
            'required': False,
            'type': 'text',

        }, {
            'name': 'email',
            'required': True,
            'type': 'text',

        }, {
            'name': 'dayOfCycle',
            'required': False,
            'type': 'text',

        }, {
            'name': 'ipAddress',
            'required': False,
            'type': 'text',

        }]
        fields = self._client.get_custom_fields({'sort': {'name', 'desc'}})
        for field in fields:
            _list.append({
                'id': field.id,
                'name': field.name,
                'required': False,
                'type': field.field_type,
                'values': field.values,
            })
        return _list

    def get_target_fields(self):
        return self.get_meta()

    def get_unsubscribe_target_fields(self):
        return [{
            'name': 'id',
            'required': True,
            'type': 'text',

        }]


class GoogleFormsController(BaseController):
    _credential = None
    _spreadsheet_id = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(GoogleFormsController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    credentials_json = self._connection_object.credentials_json
                except Exception as e:
                    print("Error getting the GoogleForms attributes 1")
                    print(e)
                    credentials_json = None
        elif not args and kwargs:
            if 'credentials_json' in kwargs:
                credentials_json = kwargs.pop('credentials_json')
        else:
            credentials_json = None
        files = None
        if credentials_json is not None:
            try:
                for s in self._plug.plug_specification.all():
                    if s.action_specification.name.lower() == 'form':
                        self._spreadsheet_id = s.value
            except:
                print("Error asignando los specifications 2")
            try:
                _json = json.dumps(credentials_json)
                self._credential = GoogleClient.OAuth2Credentials.from_json(_json)
                http_auth = self._credential.authorize(httplib2.Http())
                drive_service = discovery.build('drive', 'v3', http=http_auth)
                files = drive_service.files().list().execute()
            except Exception as e:
                print("Error getting the GoogleForms attributes 2")
                self._credential = None
                files = None
        return files is not None

    def download_to_stored_data(self, connection_object, plug, *args, **kwargs):
        if plug is None:
            plug = self._plug
        if not self._spreadsheet_id:
            return False
        sheet_values = self.get_worksheet_values()
        new_data = []
        for idx, item in enumerate(sheet_values[1:]):
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=idx + 1)
            if not q.exists():
                for idx2, cell in enumerate(item):
                    new_data.append(StoredData(name=sheet_values[0][idx2], value=cell, object_id=idx + 1,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(sheet_values)
            extra = {'controller': 'google_forms'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            # raise IndexError("hola")
            return True
        return False

    def get_sheet_list(self):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        drive_service = discovery.build('drive', 'v3', http=http_auth)
        files = drive_service.files().list().execute()
        sheet_list = tuple(
            f for f in files['files'] if 'mimeType' in f and f['mimeType'] == 'application/vnd.google-apps.spreadsheet')
        return sheet_list

    def get_worksheet_list(self, sheet_id):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        result = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        worksheet_list = tuple(i['properties'] for i in result['sheets'])
        return worksheet_list

    def get_worksheet_values(self, from_row=None, limit=None):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        range = self.get_worksheet_list(self._spreadsheet_id)
        res = sheets_service.spreadsheets().values().get(spreadsheetId=self._spreadsheet_id,
                                                         range=range[0]['title']).execute()
        values = res['values']
        if from_row is None and limit is None:
            return values
        else:
            limit = limit if limit is not None else len(values) - 1
            from_row = from_row - 1 if from_row is not None else 0
            return values[from_row:from_row + limit]
        return values

    def get_worksheet_first_row(self):
        return self.get_worksheet_values(from_row=1, limit=1)[0]

    def get_worksheet_second_row(self):
        return self.get_worksheet_values(from_row=2, limit=1)[0]

    def get_target_fields(self, **kwargs):
        return self.get_worksheet_first_row(**kwargs)


class BitbucketController(BaseController):
    _connection = None
    API_BASE_URL = 'https://api.bitbucket.org'

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(BitbucketController, self).create_connection(*args)
            if self._connection_object is not None:
                user = self._connection_object.connection_user
                password = self._connection_object.connection_password
        elif kwargs:
            user = kwargs.pop('connection_user', None)
            password = kwargs.pop('connection_password', None)
        else:
            user = password = None
        try:
            self._connection = Bitbucket(user, password)
            privileges = self._connection.get_privileges()[0]
        except Exception as e:
            print("Error getting the Bitbucket attributes")
            self._connection = None
            privileges = False
        return privileges

    def download_to_stored_data(self, connection_object=None, plug=None, issue=None, **kwargs):
        if issue is not None:
            issue_id = issue.pop('id')
            _items = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug,
                                          object_id=issue_id)
            if not q.exists():
                for k, v in issue.items():
                    obj = StoredData(connection=connection_object.connection, plug=plug,
                                     object_id=issue_id, name=k, value=v or '')
                    _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'bitbucket'}
                self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id), extra=extra)
                item.save()
        return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            for obj in data_list:
                success, result = self.create_issue(obj)
                print(success, result)
            extra = {'controller': 'bitbucket'}
            return
        raise ControllerError("Incomplete.")

    def _get_header(self):
        authorization = '{}:{}'.format(self._connection_object.connection_user,
                                       self._connection_object.connection_password)
        header = {'Accept': 'application/json',
                  'Authorization': 'Basic {0}'.format(b64encode(authorization.encode('UTF-8')).decode('UTF-8'))}
        return header

    def create_webhook(self, url='https://grplug.com/wizard/bitbucket/webhook/event/'):
        url = 'https://api.bitbucket.org/2.0/repositories/{}/{}/hooks'.format(self._connection_object.connection_user,
                                                                              self.get_repository_name())
        body = {
            'description': 'Gearplug Webhook',
            'url': url,
            'active': True,
            'events': [
                'issue:created'
            ]
        }
        r = requests.post(url, headers=self._get_header(), json=body)
        if r.status_code == 201:
            return True
        return False

    def get_repositories(self):
        url = '/2.0/repositories/{}'.format(self._connection_object.connection_user)
        r = self._request(url)
        return sorted(r['values'], key=lambda i: i['name']) if r else []

    def get_components(self):
        url = '/2.0/repositories/{}/{}/components'.format(self._connection_object.connection_user,
                                                          self.get_repository_name())
        r = self._request(url)
        return r['values'] if r else []

    def get_milestones(self):
        url = '/2.0/repositories/{}/{}/milestones'.format(self._connection_object.connection_user,
                                                          self.get_repository_name())
        r = self._request(url)
        return r['values'] if r else []

    def get_versions(self):
        url = '/2.0/repositories/{}/{}/versions'.format(self._connection_object.connection_user,
                                                        self.get_repository_name())
        r = self._request(url)
        return r['values'] if r else []

    def _get_repository(self, get_id):
        for specification in self._plug.plug_specification.all():
            if specification.action_specification.name == ('repository_id' if get_id else 'repository_name'):
                return specification.value

    def get_repository_id(self):
        return self._get_repository(True)

    def get_repository_name(self):
        return self._get_repository(False)

    def _request(self, url):
        payload = {
            'pagelen': '100'
        }
        r = requests.get(self.API_BASE_URL + url, headers=self._get_header(), params=payload)
        if r.status_code == requests.codes.ok:
            return r.json()
        return None

    def create_issue(self, fields):
        self._connection.repo_slug = self.get_repository_name()
        return self._connection.issue.create(**fields)

    def get_meta(self):
        return [{
            'name': 'title',
            'required': True,
            'type': 'text',

        }, {
            'name': 'content',
            'required': False,
            'type': 'text',
        }, {
            'name': 'kind',
            'required': True,
            'type': 'choices',
            'values': [
                'bug',
                'enhancement',
                'proposal',
                'task'
            ]
        }, {
            'name': 'priority',
            'required': True,
            'type': 'choices',
            'values': [
                'trivial',
                'minor',
                'major',
                'critical',
                'blocker'
            ]
        }, {
            'name': 'status',
            'required': False,
            'type': 'choices',
            'values': [
                'new',
                'open',
                'resolved',
                'on hold',
                'invalid',
                'duplicate',
                'wontfix'
            ]
        }, {
            'name': 'component',
            'required': False,
            'type': 'choices',
            'values': [c['name'] for c in self.get_components()]
        }, {
            'name': 'milestone',
            'required': False,
            'type': 'choices',
            'values': [m['name'] for m in self.get_milestones()]
        }, {
            'name': 'version',
            'required': False,
            'type': 'choices',
            'values': [v['name'] for v in self.get_versions()]
        }]

    def get_target_fields(self):
        return self.get_meta()


class MailChimpController(BaseController):
    """
    MailChimpController Class
    """
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MailChimpController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    print(self._connection_object.connection_user, self._connection_object.api_key)
                    self._client = MailChimp(self._connection_object.connection_user, self._connection_object.api_key)
                except Exception as e:
                    print("Error getting the MailChimp attributes")
                    self._client = None
        elif not args and kwargs:
            if 'user' in kwargs:
                user = kwargs.pop('user')
            if 'api_key' in kwargs:
                api_key = kwargs.pop('api_key')
            try:
                self._client = MailChimp(user, api_key)
                print("%s %s", (user, api_key))
                print(self._client)
            except Exception as e:
                print(e)
                print("Error getting the MailChimp attributes")
                self._client = None
        t = self.get_lists()
        return t is not None

    def get_lists(self):
        if self._client:
            result = self._client.lists.all()
            try:
                return [{'name': l['name'], 'id': l['id']} for l in result['lists']]
            except:
                return []
        return []

    def get_list_merge_fields(self, list_id):
        result = self._client.lists._mc_client._get(url='lists/%s/merge-fields' % list_id)
        try:
            return result['merge_fields']
        except:
            return []

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
                except:
                    data_list = []
        if self._plug is not None:
            status = None
            _list = None
            for specification in self._plug.plug_specification.all():
                if specification.action_specification.action.name == 'subscribe':
                    status = 'subscribed'
                elif specification.action_specification.action.name == 'unsubscribe':
                    status = 'unsubscribed'
                    _list = self.get_all_members(self._plug.plug_specification.all()[0].value)

            list_id = self._plug.plug_specification.all()[0].value
            for obj in data_list:
                d = {'email_address': obj.pop('email_address'), 'status': status,
                     'merge_fields': {key: obj[key] for key in obj.keys()}}
                obj_list.append(d)

            if status == 'unsubscribed':
                obj_list = self.set_members_hash_id(obj_list, _list)

            extra = {'controller': 'mailchimp'}
            for item in obj_list:
                try:
                    if status == 'subscribed':
                        res = self._client.lists.members.create(list_id, item)
                    elif status == 'unsubscribed':
                        res = self._client.lists.members.update(list_id, item['hash_id'], {'status': 'unsubscribed'})
                    extra['status'] = "s"
                    self._log.info('Email: %s  successfully sent. Result: %s.' % (item['email_address'], res['id']),
                                   extra=extra)
                except Exception as e:
                    print(e)
                    res = "User already exists"
                    extra['status'] = 'f'
                    self._log.error('Email: %s  failed. Result: %s.' % (item['email_address'], res), extra=extra)
            return
        raise ControllerError("Incomplete.")

    def get_target_fields(self, **kwargs):
        return self.get_list_merge_fields(**kwargs)

    def get_all_members(self, list_id):
        return self._client.lists.members.all(list_id, get_all=True, fields="members.id,members.email_address")

    def set_members_hash_id(self, members, _list):
        return [dict(m, hash_id=l['id']) for m in members for l in _list['members'] if
                m['email_address'] == l['email_address']]


class FacebookController(BaseController):
    _app_id = FACEBOOK_APP_ID
    _app_secret = FACEBOOK_APP_SECRET
    _base_graph_url = 'https://graph.facebook.com'
    _token = None
    _page = None
    _form = None

    def __init__(self, *args):
        super(FacebookController, self).__init__(*args)

    def create_connection(self, *args, **kwargs):
        if args:
            super(FacebookController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                except Exception as e:
                    print("Error getting the Facebook token")
                    # raise
        elif kwargs:
            try:
                self._token = kwargs.pop('token')
            except Exception as e:
                print("Error getting the Facebook token")
        try:
            if self._plug is not None:
                for s in self._plug.plug_specification.all():
                    if s.action_specification.name.lower() == 'page':
                        self._page = s.value
                    if s.action_specification.name.lower() == 'form':
                        self._form = s.value
                        # else:
                        #     print("There is no Plug asigned to the FacebookController")
        except:
            print("Error asignando los specifications")

        try:
            object_list = self.get_account(self._token).json()
            if 'id' in object_list:
                return True
        except Exception as e:
            return False
        return False

    def _get_app_secret_proof(self, access_token):
        h = hmac.new(
            self._app_secret.encode('utf-8'),
            msg=access_token.encode('utf-8'),
            digestmod=hashlib.sha256
        )
        return h.hexdigest()

    def _send_request(self, url='', token='', base_url='', params=[], from_date=None):
        if not base_url:
            base_url = self._base_graph_url
        if not params:
            params = {'access_token': token, 'appsecret_proof': self._get_app_secret_proof(token)}
        if from_date is not None:
            params['from_date'] = from_date
        graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)
        graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)
        r = requests.get('%s/v%s/%s' % (base_url, FACEBOOK_GRAPH_VERSION, url),
                         params=params)
        try:
            return json.loads(r.text)['data']
        except KeyError:
            return r
        except Exception as e:
            print(e)
            return []

    def extend_token(self, token):
        url = 'oauth/access_token'
        params = {'grant_type': 'fb_exchange_token',
                  'client_id': self._app_id,
                  'client_secret': self._app_secret,
                  'fb_exchange_token': token}
        r = self._send_request(url=url, params=params)
        try:
            return json.loads(r.text)['access_token']
        except Exception as e:
            print(e)
            return ''

    def get_account(self, access_token):
        url = 'me'
        return self._send_request(url=url, token=access_token)

    def get_pages(self, access_token):
        url = 'me/accounts'
        return self._send_request(url=url, token=access_token)

    def get_leads(self, access_token, form_id, from_date=None):
        url = '%s/leads' % form_id
        return self._send_request(url=url, token=access_token, from_date=from_date)

    def get_forms(self, access_token, page_id):
        url = '%s/leadgen_forms' % page_id
        return self._send_request(url=url, token=access_token)

    def download_to_stored_data(self, connection_object, plug, from_date=None):
        if plug is None:
            plug = self._plug
        if from_date is not None:
            from_date = int(time.mktime(from_date.timetuple()) * 1000)
            # print('from_date: %s' % from_date)

        leads = self.get_leads(connection_object.token, self._form, from_date=from_date)
        new_data = []
        for item in leads:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                for column in item['field_data']:
                    new_data.append(StoredData(name=column['name'], value=column['values'][0], object_id=item['id'],
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(leads[0]['field_data'])
            entries = len(new_data) // field_count
            extra = {'controller': 'facebook'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            return True
        return False


class MySQLController(BaseController):
    _connection = None
    _database = None
    _table = None
    _cursor = None

    def __init__(self, *args, **kwargs):
        super(MySQLController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MySQLController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    pass
                    # raise
                    print("Error getting the MySQL attributes")
        elif not args and kwargs:
            try:
                host = kwargs.pop('host')
                port = kwargs.pop('port')
                user = kwargs.pop('connection_user')
                password = kwargs.pop('connection_password')
                self._database = kwargs.pop('database')
                self._table = kwargs.pop('table', None)
            except Exception as e:
                pass
                # raise
                print("Error getting the MySQL attributes")
        try:
            self._connection = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=self._database)
            self._cursor = self._connection.cursor()
        except:
            self._connection = None
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute('DESCRIBE `%s`.`%s`' % (self._database, self._table))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2], 'is_primary': item[3] == 'PRI'} for
                        item in self._cursor]
            except:
                print('Error describing table: %s')
        return []

    def get_primary_keys(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute('DESCRIBE `%s`.`%s`' % (self._database, self._table))
                return [item[0] for item in self._cursor if item[3] == 'PRI']
            except:
                print('Error ')
        return None

    def select_all(self, limit=50):
        if self._table is not None and self._database is not None and self._plug is not None:
            try:
                order_by = self._plug.plug_specification.all()[0].value
            except:
                order_by = None
            select = 'SELECT * FROM `%s`.`%s`' % (self._database, self._table)
            if order_by is not None:
                select += 'ORDER BY %s DESC ' % order_by
            if limit is not None and isinstance(limit, int):
                select += 'LIMIT %s' % limit
            try:
                self._cursor.execute(select)
                cursor_select_all = copy.copy(self._cursor)
                self.describe_table()
                cursor_describe = self._cursor
                return [{column[0]: item[i] for i, column in enumerate(cursor_describe)} for item in cursor_select_all]
            except Exception as e:
                print(e)
        return []

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        if plug is None:
            plug = self._plug
        data = self.select_all()
        id_list = self.get_primary_keys()
        parsed_data = [{'id': tuple(item[key] for key in id_list),
                        'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]}
                       for item in data]
        new_data = []
        for item in parsed_data:
            try:
                id_item = item['id'][0]
            except IndexError:
                id_item = None
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id_item)
            if not q.exists():
                for column in item['data']:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=id_item,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(parsed_data[0]['data'])
            extra = {'controller': 'mysql'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            return True
        return False

    def _get_insert_statement(self, item):
        insert = """INSERT INTO `%s`(%s) VALUES (%s)""" % (
            self._table, """,""".join(item.keys()), """,""".join("""\"%s\"""" % i for i in item.values()))
        return insert

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
                except:
                    data_list = []
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'mysql'}
            for item in data_list:
                try:
                    insert = self._get_insert_statement(item)
                    self._cursor.execute(insert)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (self._cursor.lastrowid), extra=extra)
                    obj_list.append(self._cursor.lastrowid)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (self._cursor.lastrowid), extra=extra)
            try:
                self._connection.commit()
            except:
                self._connection.rollback()
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, **kwargs):
        return self.describe_table(**kwargs)


class PostgreSQLController(BaseController):
    _connection = None
    _database = None
    _table = None
    _cursor = None

    def __init__(self, *args, **kwargs):
        super(PostgreSQLController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(PostgreSQLController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    pass
                    # raise
                    print("Error getting the PostgreSQL attributes")
        elif not args and kwargs:
            try:
                host = kwargs.pop('host')
                port = kwargs.pop('port')
                user = kwargs.pop('connection_user')
                password = kwargs.pop('connection_password')
                self._database = kwargs.pop('database')
                self._table = kwargs.pop('table', None)
            except Exception as e:
                pass
                # raise
                print("Error getting the PostgreSQL attributes")
        try:
            self._connection = psycopg2.connect(host=host, port=int(port), user=user, password=password,
                                                database=self._database)
            self._cursor = self._connection.cursor()
        except:
            self._connection = None
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    "SELECT column_name, data_type, is_nullable FROM INFORMATION_SCHEMA.columns WHERE table_schema= %s AND table_name = %s",
                    self._table.split('.'))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for
                        item in self._cursor]
            except:
                print('Error describing table: %s')
        return []

    def get_primary_keys(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    "SELECT c.column_name FROM information_schema.table_constraints tc JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name) JOIN information_schema.columns AS c ON c.table_schema = tc.constraint_schema AND tc.table_name = c.table_name AND ccu.column_name = c.column_name where c.table_schema = %s and tc.table_name = %s",
                    self._table.split('.'))
                return [item[0] for item in self._cursor]
            except Exception as e:
                print('Error ')
        return None

    def select_all(self, limit=50):
        if self._table is not None and self._database is not None and self._plug is not None:
            try:
                order_by = self._plug.plug_specification.all()[0].value
            except:
                order_by = None
            select = 'SELECT * FROM %s ' % self._table
            if order_by is not None:
                select += 'ORDER BY %s DESC ' % order_by
            if limit is not None and isinstance(limit, int):
                select += 'LIMIT %s' % limit
            try:
                self._cursor.execute(select)
                cursor_select_all = [item for item in self._cursor]
                cursor_describe = self.describe_table()
                return [{column['name']: item[i] for i, column in enumerate(cursor_describe)} for item in
                        cursor_select_all]
            except Exception as e:
                print(e)
        return []

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        if plug is None:
            plug = self._plug
        data = self.select_all()
        id_list = self.get_primary_keys()
        parsed_data = [{'id': tuple(item[key] for key in id_list),
                        'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]}
                       for item in data]
        new_data = []
        for item in parsed_data:
            try:
                id_item = item['id'][0]
            except IndexError:
                id_item = None
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id_item)
            if not q.exists():
                for column in item['data']:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=id_item,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(parsed_data[0]['data'])
            extra = {'controller': 'postgresql'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            return True
        return False

    def _get_insert_statement(self, item):
        insert = """INSERT INTO %s (%s) VALUES (%s)""" % (
            self._table, """,""".join(item.keys()), """,""".join("""\'%s\'""" % i for i in item.values()))
        return insert

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
                except:
                    data_list = []
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'postgresql'}
            for item in data_list:
                try:
                    insert = self._get_insert_statement(item)
                    self._cursor.execute(insert)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (self._cursor.lastrowid), extra=extra)
                    obj_list.append(self._cursor.lastrowid)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (self._cursor.lastrowid), extra=extra)
            try:
                self._connection.commit()
            except:
                self._connection.rollback()
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, **kwargs):
        return self.describe_table(**kwargs)


class MSSQLController(BaseController):
    _connection = None
    _database = None
    _table = None
    _cursor = None

    def __init__(self, *args, **kwargs):
        super(MSSQLController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(MSSQLController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self._database = self._connection_object.database
                    self._table = self._connection_object.table
                except Exception as e:
                    pass
                    # raise
                    print("Error getting the MSSQL attributes")
        elif not args and kwargs:
            try:
                host = kwargs.pop('host')
                port = kwargs.pop('port')
                user = kwargs.pop('connection_user')
                password = kwargs.pop('connection_password')
                self._database = kwargs.pop('database')
                self._table = kwargs.pop('table', None)
            except Exception as e:
                pass
                # raise
                print("Error getting the MSSQL attributes")
        try:
            self._connection = pymssql.connect(host=host, port=int(port), user=user, password=password,
                                               database=self._database)
            self._cursor = self._connection.cursor()
        except:
            self._connection = None
        return self._connection is not None

    def describe_table(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    'select COLUMN_NAME, DATA_TYPE, IS_NULLABLE from information_schema.columns where table_name = %s',
                    (self._table,))
                return [{'name': item[0], 'type': item[1], 'null': 'YES' == item[2]} for
                        item in self._cursor]
            except:
                print('Error describing table: %s')
        return []

    def get_primary_keys(self):
        if self._table is not None and self._database is not None:
            try:
                self._cursor.execute(
                    "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE WHERE OBJECTPROPERTY(OBJECT_ID(CONSTRAINT_SCHEMA + '.' + CONSTRAINT_NAME), 'IsPrimaryKey') = 1 AND TABLE_NAME = %s",
                    (self._table,))
                return [item[0] for item in self._cursor]
            except:
                print('Error ')
        return None

    def select_all(self, limit=50):
        if self._table is not None and self._database is not None and self._plug is not None:
            try:
                order_by = self._plug.plug_specification.all()[0].value
            except:
                order_by = None
            select = 'SELECT * FROM %s ' % self._table
            if order_by is not None:
                select += 'ORDER BY %s DESC ' % order_by
            if limit is not None and isinstance(limit, int):
                select += 'OFFSET 0 ROWS FETCH NEXT %s ROWS ONLY' % limit
            try:
                self._cursor.execute(select)
                cursor_select_all = [item for item in self._cursor]
                cursor_describe = self.describe_table()
                return [{column['name']: item[i] for i, column in enumerate(cursor_describe)} for item in
                        cursor_select_all]
            except Exception as e:
                print(e)
        return []

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        if plug is None:
            plug = self._plug
        data = self.select_all()
        id_list = self.get_primary_keys()
        parsed_data = [{'id': tuple(item[key] for key in id_list),
                        'data': [{'name': key, 'value': item[key]} for key in item.keys() if key not in id_list]}
                       for item in data]
        new_data = []
        for item in parsed_data:
            try:
                id_item = item['id'][0]
            except IndexError:
                id_item = None
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=id_item)
            if not q.exists():
                for column in item['data']:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=id_item,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(parsed_data[0]['data'])
            extra = {'controller': 'mssql'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            return True
        return False

    def _get_insert_statement(self, item):
        insert = """INSERT INTO %s (%s) VALUES (%s)""" % (
            self._table, """,""".join(item.keys()), """,""".join("""\'%s\'""" % i for i in item.values()))
        return insert

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
                except:
                    data_list = []
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'mssql'}
            for item in data_list:
                try:
                    insert = self._get_insert_statement(item)
                    self._cursor.execute(insert)
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (self._cursor.lastrowid), extra=extra)
                    obj_list.append(self._cursor.lastrowid)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (self._cursor.lastrowid), extra=extra)
            try:
                self._connection.commit()
            except:
                self._connection.rollback()
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self):
        return self.describe_table()


class CustomSugarObject(sugarcrm.SugarObject):
    module = "CustomObject"

    def __init__(self, *args, **kwargs):
        if args:
            self.module = args[0]
        return super(CustomSugarObject, self).__init__(**kwargs)

    @property
    def query(self):
        return ''


class SugarCRMController(BaseController):
    _user = None
    _password = None
    _url = None
    _session = None
    _module = None

    def __init__(self, *args, **kwargs):
        super(SugarCRMController, self).__init__(*args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(SugarCRMController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._user = self._connection_object.connection_user
                    self._password = self._connection_object.connection_password
                    self._url = self._connection_object.url
                except Exception as e:
                    print("Error getting the SugarCRM attributes")
                try:
                    self._module = args[2]
                except:
                    pass
        elif not args and kwargs:
            try:
                self._user = kwargs.pop('connection_user')
                self._password = kwargs.pop('connection_password')
                self._url = kwargs.pop('url')
            except Exception as e:
                print("Error getting the SugarCRM attributes")
        if self._url is not None and self._user is not None and self._password is not None:
            self._session = sugarcrm.Session(self._url, self._user, self._password)
        return self._session is not None and self._session.session_id is not None

    def get_available_modules(self):
        return self._session.get_available_modules()

    def get_entries(self, module_name, id_list):
        return self._session.get_entries(module_name, id_list)

    def get_entry_list(self, module, **kwargs):
        custom_module = CustomSugarObject(module)
        return self._session.get_entry_list(custom_module, **kwargs)

    def get_module_fields(self, module, **kwargs):
        custom_module = CustomSugarObject(module)
        return self._session.get_module_fields(custom_module, **kwargs)

    def set_entry(self, obj):
        return self._session.set_entry(obj)

    def set_entries(self, obj_list):
        return self._session.set_entries(obj_list)

    def download_to_stored_data(self, connection_object, plug, limit=29, order_by="date_entered DESC", **kwargs):
        module = plug.plug_specification.all()[0].value  # Especificar que specification
        data = self.get_entry_list(module, max_results=limit, order_by=order_by)
        new_data = []
        for item in data:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item.id)
            if not q.exists():
                for column in item.fields:
                    new_data.append(StoredData(name=column['name'], value=column['value'], object_id=item.id,
                                               connection=connection_object.connection, plug=plug))
        if new_data:
            field_count = len(data[0].fields)
            extra = {'controller': 'sugarcrm'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
            return True
        return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
                except:
                    data_list = []
        if self._plug is not None:
            obj_list = []
            module_name = self._plug.plug_specification.all()[0].value
            extra = {'controller': 'sugarcrm'}
            for item in data_list:
                try:
                    res = self.set_entry(CustomSugarObject(module_name, **item))
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (res.id), extra=extra)
                    obj_list.append(id)
                except Exception as e:
                    print(e)
                    extra['status'] = 'f'
                    self._log.info('Item: %s failed to send.' % (res.id), extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def get_target_fields(self, module, **kwargs):
        return self.get_module_fields(module, **kwargs)


class ControllerError(Exception):
    pass


def get_dict_with_source_data(source_data, target_fields, include_id=False):
    pattern = re.compile("^(\%\%\S+\%\%)$")
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
                if w in ['%%%%%s%%%%' % k for k in obj['data'].keys()]:
                    values.append(obj['data'][w.replace('%', '')])
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
    # print("lista: ",lista)
    return _recursive_xml_to_dict(lista)


def _recursive_xml_to_dict(lista):
    lista_dict = []
    # regex = re.compile('{(https?|ftp|http?)://(-\.)?([^\s/?\.#-]+\.?)+(/[^\s]*)?}(\S+)')
    regex = re.compile('^{(\S+)}(\S+)')
    for e in lista:
        result = regex.match(e.tag)
        if result is not None:  # and result.group(5) != 'link':
            dict_e = {'tag': result.group(2), 'attrib': e.attrib, 'text': e.text, 'content': _recursive_xml_to_dict(e)}
            lista_dict.append(dict_e)
    return lista_dict