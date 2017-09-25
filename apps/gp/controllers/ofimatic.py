from apps.gp.controllers.base import BaseController, GoogleBaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import StoredData, GooglePushWebhook, ActionSpecification, \
    Webhook, PlugActionSpecification, Plug
from django.db.models import Q
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
import httplib2
from oauth2client import client as GoogleClient
from dateutil.parser import parse
from django.conf import settings
from django.urls import reverse
import pytz
import requests
from apiclient import discovery
import json
import uuid
from evernote.api.client import EvernoteClient
import wunderpy2
import evernote.edam.type.ttypes as Types
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from collections import OrderedDict
from evernote.edam.type.ttypes import NoteSortOrder
from django.conf import settings
import re
from django.shortcuts import HttpResponse


class GoogleSpreadSheetsController(GoogleBaseController):
    _credential = None
    _spreadsheet_id = None
    _worksheet_name = None

    def __init__(self, connection=None, plug=None, **kwargs):
        GoogleBaseController.__init__(self, connection=connection, plug=plug,
                                      **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        credentials_json = None
        super(GoogleSpreadSheetsController, self).create_connection(
            connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                credentials_json = self._connection_object.credentials_json
                if self._plug is not None:
                    try:
                        self._spreadsheet_id = self._plug.plug_action_specification.get(
                            action_specification__name__iexact='spreadsheet').value
                        self._worksheet_name = self._plug.plug_action_specification.get(
                            action_specification__name__iexact='worksheet').value
                    except Exception as e:
                        print("Error asignando los specifications GoogleSpreadSheets 2")
            except Exception as e:
                print("Error getting the GoogleSpreadSheets attributes 1")
                print(e)
                credentials_json = None
        if credentials_json is not None:
            self._credential = GoogleClient.OAuth2Credentials.from_json(
                json.dumps(credentials_json))

    def test_connection(self):
        try:
            self._refresh_token()
            http_auth = self._credential.authorize(httplib2.Http())
            drive_service = discovery.build('drive', 'v3', http=http_auth)
            files = drive_service.files().list().execute()
        except GoogleClient.HttpAccessTokenRefreshError:
            self._report_broken_token()
            files = None
        return files is not None

    def download_to_stored_data(self, connection_object, plug, *args,
                                **kwargs):
        if plug is None:
            plug = self._plug
        if not self._spreadsheet_id or not self._worksheet_name:
            return False
        sheet_values = self.get_worksheet_values()
        new_data = []
        for idx, item in enumerate(sheet_values[1:]):
            q = StoredData.objects.filter(
                connection=connection_object.connection, plug=plug,
                object_id=idx + 1)
            if not q.exists():
                try:
                    for idx2, cell in enumerate(item):
                        new_data.append(StoredData(name=sheet_values[0][idx2], value=cell, object_id=idx + 1,
                                                   connection=connection_object.connection, plug=plug))
                except IndexError as e:
                    raise ControllerError(code=0, controller=self.connector,
                                          message='Los valores no corresponden con los campos existentes.'.format(
                                              str(e)))
        if new_data:
            field_count = len(sheet_values)
            extra = {'controller': 'google_spreadsheets'}
            for i, item in enumerate(new_data):
                try:
                    item.save()
                    if (i + 1) % field_count == 0:
                        extra['status'] = 's'
                        self._log.info(
                            'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                                item.object_id, item.plug.id,
                                item.connection.id), extra=extra)
                except:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                            item.object_id, item.name, item.plug.id,
                            item.connection.id), extra=extra)
            # raise IndexError("hola")
            return True
        return False

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        first_row = self.get_worksheet_first_row()
        ordered_target_fields = OrderedDict()
        for field in first_row:
            for k in target_fields.keys():
                if k == field:
                    if target_fields[k] == '':
                        target_fields[k] = ' '
                    ordered_target_fields[k] = target_fields[k]
                    break
        data_list = get_dict_with_source_data(source_data,
                                              ordered_target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[0]]
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
            return True
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
            f for f in files['files'] if 'mimeType' in f and f[
                'mimeType'] == 'application/vnd.google-apps.spreadsheet')
        return sheet_list

    def get_worksheet_list(self, sheet_id):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        result = sheets_service.spreadsheets().get(
            spreadsheetId=sheet_id).execute()
        worksheet_list = tuple(i['properties'] for i in result['sheets'])
        return worksheet_list

    def get_worksheet_values(self, from_row=None, limit=None):
        credential = self._credential
        http_auth = credential.authorize(httplib2.Http())
        sheets_service = discovery.build('sheets', 'v4', http=http_auth)
        res = sheets_service.spreadsheets().values().get(
            spreadsheetId=self._spreadsheet_id,
            range='{0}'.format(self._worksheet_name)).execute()
        # TODO try para ver si llego la data. Sino levantar error de mala configuracion en la hoja de calculo
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
        _range = "{0}!A{1}:{2}{1}".format(
            self._worksheet_name, idx, self.colnum_string(len(row)))
        res = sheets_service.spreadsheets().values().update(
            spreadsheetId=self._spreadsheet_id,
            range=_range, valueInputOption='RAW',
            body=body).execute()
        return res

    def get_target_fields(self, **kwargs):
        return self.get_worksheet_first_row(**kwargs)

    def get_mapping_fields(self, **kwargs):
        fields = self.get_worksheet_first_row()
        return [
            MapField({"name": f}, controller=ConnectorEnum.GoogleSpreadSheets)
            for f in fields]

    def get_action_specification_options(self, action_specification_id,
                                         **kwargs):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        print("GSS->", action_specification.name, kwargs)
        if action_specification.name.lower() == 'spreadsheet':
            return tuple({'id': p['id'], 'name': p['name']} for p in
                         self.get_sheet_list())
        elif action_specification.name.lower() == 'worksheet':

            return tuple({'id': p['title'], 'name': p['title']} for p in
                         self.get_worksheet_list(**kwargs))
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")


class GoogleCalendarController(GoogleBaseController):
    _connection = None
    _credential = None

    def __init__(self, connection=None, plug=None, **kwargs):
        GoogleBaseController.__init__(self, connection=connection, plug=plug,
                                      **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        credentials_json = None
        super(GoogleCalendarController, self).create_connection(
            connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                credentials_json = self._connection_object.credentials_json
            except Exception as e:
                print("Error GoogleCalendar attributes {}".format(e))
        if credentials_json is not None:
            self._credential = GoogleClient.OAuth2Credentials.from_json(
                json.dumps(credentials_json))

    def test_connection(self):
        try:
            self._refresh_token()
            calendar_list = self._connection.calendarList().list().execute()
            calendars = calendar_list['items']
        except GoogleClient.HttpAccessTokenRefreshError:
            self._report_broken_token()
            calendars = None
        except Exception as e:
            print("Error Test connection GoogleCalendar")
            calendars = None
        return calendars is not None

    def download_to_stored_data(self, connection_object=None, plug=None,
                                events=None, **kwargs):
        if events is not None:
            _items = []
            for event in events:
                q = StoredData.objects.filter(
                    connection=connection_object.connection, plug=plug,
                    object_id=event['id'])
                if not q.exists():
                    for k, v in event.items():
                        obj = StoredData(
                            connection=connection_object.connection, plug=plug,
                            object_id=event['id'], name=k, value=v or '')
                        _items.append(obj)
            extra = {}
            for item in _items:
                extra['status'] = 's'
                extra = {'controller': 'googlecalendar'}
                self._log.info(
                    'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                        item.object_id, item.plug.id, item.connection.id),
                    extra=extra)
                item.save()
        return False

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
                res = self.create_issue(
                    self._plug.plug_action_specification.all()[0].value, obj)
            extra = {'controller': 'googlecalendar'}
            return
        raise ControllerError("Incomplete.")

    def create_issue(self, calendar_id, event):
        if 'start_dateTime' in event:
            start_datetime = event.pop('start_dateTime')
            if 'start' not in event:
                event['start'] = {
                    'dateTime': self._parse_datetime(start_datetime)}
            else:
                event['start']['dateTime'] = self._parse_datetime(
                    start_datetime)
        if 'start_timeZone' in event:
            start_timezone = event.pop('start_timeZone')
            if 'start' not in event:
                event['start'] = {'timeZone': start_timezone}
            else:
                event['start']['timeZone'] = start_timezone
        if 'end_dateTime' in event:
            end_datetime = event.pop('end_dateTime')
            if 'end' not in event:
                event['end'] = {'dateTime': self._parse_datetime(end_datetime)}
            else:
                event['end']['dateTime'] = self._parse_datetime(end_datetime)
        if 'end_timeZone' in event:
            end_timezone = event.pop('end_timeZone')
            if 'end' not in event:
                event['end'] = {'timeZone': end_timezone}
            else:
                event['end']['timeZone'] = end_timezone
        return self._connection.events().insert(calendarId=calendar_id,
                                                body=event).execute()

    def _parse_datetime(self, datetime):
        return parse(datetime).strftime('%Y-%m-%dT%H:%M:%S%z')

    def get_calendar_list(self):
        calendar_list = self._connection.calendarList().list().execute()
        _list = []
        for c in calendar_list['items']:
            c['name'] = c['summary']
            _list.append(c)
        calendars = tuple(c for c in _list)
        return calendars

    def create_webhook(self):
        calendar_id = self._plug.plug_action_specification.first().value
        url = 'https://www.googleapis.com/calendar/v3/calendars/{}/events/watch'.format(
            calendar_id)
        webhook = Webhook.objects.create(name='googlecalendar',
                                         plug=self._plug, url='')
        headers = {
            'Authorization': 'Bearer {}'.format(
                self._connection_object.credentials_json['access_token']),
            'Content-Type': 'application/json'
        }

        body = {
            "id": webhook.id,
            "type": "web_hook",
            "address": "{0}/webhook/googlecalendar/{1}/".format(
                settings.WEBHOOK_HOST, webhook.id),
        }
        r = requests.post(url, headers=headers, json=body)
        if r.status_code in [200, 201]:
            data = r.json()
            # GooglePushWebhook.objects.create(connection=self._connection_object.connection, channel_id=data['id'],
            #                                  resource_id=data['resourceId'], expiration=data['expiration'])
            webhook.url = "{0}/webhook/googlecalendar/{1}/".format(
                settings.WEBHOOK_HOST, webhook.id)
            webhook.generated_id = data['resourceId']
            webhook.is_active = True
            webhook.expiration = data['expiration']
            webhook.save(update_fields=['url', 'generated_id', 'is_active',
                                        'expiration'])
        else:
            webhook.is_deleted = True
            webhook.save(update_fields=['is_deleted', ])
            return True
        return False

    def get_events(self, limit=10):
        calendar_id = self._plug.plug_action_specification.get(
            action_specification__name__iexact='calendar').value
        eventsResult = self._connection.events().list(
            calendarId=calendar_id, maxResults=limit, singleEvents=True,
            orderBy='updated').execute()
        return eventsResult.get('items', None)

    def get_meta(self):
        _list = [{
            'name': 'summary',
            'required': False,
            'type': 'text',
        }, {
            'name': 'location',
            'required': False,
            'type': 'text',
        }, {
            'name': 'description',
            'required': False,
            'type': 'text',
        }, {
            'name': 'start_dateTime',
            'required': False,
            'type': 'text',
        }, {
            'name': 'start_timeZone',
            'required': False,
            'type': 'text',
            'values': [tz for tz in pytz.all_timezones]
        }, {
            'name': 'end_dateTime',
            'required': False,
            'type': 'text',
        }, {
            'name': 'end_timeZone',
            'required': False,
            'type': 'text',
            'values': [tz for tz in pytz.all_timezones]
        }]
        return _list

    def get_target_fields(self):
        return self.get_meta()

    def get_mapping_fields(self, **kwargs):
        fields = self.get_meta()
        return [MapField(f, controller=ConnectorEnum.GoogleCalendar) for f in
                fields]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        calendar_list = self._connection.calendarList().list().execute()
        if action_specification.name.lower() == "calendar":
            return tuple({"name": c["summary"], "id": c["id"]} for c in
                         calendar_list['items'])
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")


class EvernoteController(BaseController):
    _token = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(EvernoteController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                except Exception as e:
                    print("Error getting the Evernote token")

    def test_connection(self):
        client = EvernoteClient(self._token)
        try:
            client.get_note_store()
            return self._token is not None
        except Exception as e:
            return self._token is None

    def download_to_stored_data(self, connection_object, plug, list=None):
        print("source from evernote")
        notes = self.get_notes(self._token)
        print("notes")
        print(notes)
        new_data = []
        for item in notes:
            q = StoredData.objects.filter(
                connection=connection_object.connection, plug=plug,
                object_id=item['id'])
            if not q.exists():
                for column in item:
                    new_data.append(StoredData(name=column, value=item[column],
                                               object_id=item['id'],
                                               connection=connection_object.connection,
                                               plug=plug))
        extra = {}
        for item in new_data:
            extra['status'] = 's'
            extra = {'controller': 'evernote'}
            self._log.info(
                'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                    item.object_id, item.plug.id, item.connection.id),
                extra=extra)
            item.save()
        return False

    def get_notes(self, token):
        authToken = token
        client = EvernoteClient(token=token)
        noteStore = client.get_note_store()
        filter = NoteFilter()
        filter.ascending = False
        spec = NotesMetadataResultSpec()
        spec.includeTitle = True
        ourNoteList = noteStore.findNotesMetadata(token, filter, 0, 100, spec)
        list = []
        for note in ourNoteList.notes:
            wholenote = noteStore.getNote(
                authToken, note.guid, True, True, True, True)
            m = re.findall('<en-note[^>]*>(.*?)<\/en-note>', str(wholenote))
            note = {'title': note.title, 'id': note.guid, 'content': m[0]}
            list.append(note)
        return list

    def get_target_fields(self, **kwargs):
        return [{'name': 'title', 'type': 'varchar', 'required': True},
                {'name': 'content', 'type': 'varchar', 'required': True}]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.Evernote) for f in fields]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'evernote'}
            for item in data_list:
                note = self.create_note(item)
                if note.guid:
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' %
                                   (note.guid), extra=extra)
                    obj_list.append(note.guid)
                else:
                    extra['status'] = 'f'
                    self._log.info('Item: failed to send.', extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def create_note(self, data):
        client = EvernoteClient(token=self._token)
        c = data['content']
        noteStore = client.get_note_store()
        note = Types.Note()
        note.title = data['title']
        note.content = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
        note.content += '<en-note>' + c + '</en-note>'
        return noteStore.createNote(note)


class WunderListController(BaseController):
    _token = None
    _api = wunderpy2.WunderApi()
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(WunderListController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(WunderListController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            self._token = self._connection_object.token

    def test_connection(self):
        self._client = self._api.get_client(
            self._token, settings.WUNDERLIST_CLIENT_ID)
        try:
            a = self.get_lists()
            return self._token is not None
        except Exception as e:
            return self._token is None

    def get_lists(self):
        response = self._client.authenticated_request(
            self._client.api.Endpoints.LISTS)
        a = response.json()
        return a

    def get_task(self, id):
        headers = {
            'X-Access-Token': self._token,
            'X-Client-ID': settings.WUNDERLIST_CLIENT_ID
        }
        response = requests.get(
            'http://a.wunderlist.com/api/v1/tasks/{0}'.format(str(id)),
            headers=headers)
        return response.json()

    def create_task(self, **kwargs):
        _list_id = int(kwargs['parents'])
        _title = str(kwargs['title'])

        data = {'list_id': _list_id, 'title': _title}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain',
                   'X-Access-Token': self._token,
                   'X-Client-ID': settings.WUNDERLIST_CLIENT_ID}

        response = requests.post('http://a.wunderlist.com/api/v1/tasks',
                                 data=json.dumps(data), headers=headers)
        return response

    def update_task(self):

        data = {'list_id': self._list_id, 'title': self._title}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain',
                   'X-Access-Token': self._token,
                   'X-Client-ID': settings.WUNDERLIST_CLIENT_ID}

        response = requests.post('http://a.wunderlist.com/api/v1/tasks',
                                 data=json.dumps(data), headers=headers)
        return response
        pass

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'list':
            return tuple(
                {'id': l['id'], 'name': l['title']} for l in self.get_lists())
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

    def create_webhook(self):
        action = self._plug.action.name
        if action == 'completed task' or action == "new task":
            list_id = self._plug.plug_action_specification.get(action_specification__name='list')
            webhook = Webhook.objects.create(
                name='wunderlist', plug=self._plug, url='')
            url_base = settings.WEBHOOK_HOST
            url_path = reverse('home:webhook',
                               kwargs={'connector': 'wunderlist',
                                       'webhook_id': webhook.id})
            headers = {
                'X-Access-Token': self._token,
                'X-Client-ID': settings.WUNDERLIST_CLIENT_ID
            }
            body_data = {
                'list_id': int(list_id.value),
                'url': url_base + url_path,
                'processor_type': 'generic',
                'configuration': ''
            }
            response = requests.post(
                'http://a.wunderlist.com/api/v1/webhooks', headers=headers,
                data=body_data)
            if response.status_code == 201:
                webhook.generated_id = response.json()['id']
                webhook.url = response.json()['url']
                webhook.is_active = True
                webhook.save(
                    update_fields=['url', 'generated_id', 'is_active'])
        return True

    def list_webhooks(self):
        action = self._plug.action.name
        if action == 'completed task':
            list_id = self._plug.plug_action_specification.get(
                action_specification__name='task list')
            headers = {
                'X-Access-Token': self._token,
                'X-Client-ID': settings.WUNDERLIST_CLIENT_ID
            }
            body_data = {
                'list_id': int(list_id.value),
            }
            response = requests.get(
                'http://a.wunderlist.com/api/v1/webhooks', headers=headers,
                data=body_data)
            return (response.json())

    # Metodo de borrado de webhooks, utilizacion manual.
    def delete_webhooks(self):
        webhook_list = self.list_webhooks()
        if len(webhook_list) > 0:
            for wh in webhook_list:
                headers = {
                    'X-Access-Token': self._token,
                    'X-Client-ID': settings.WUNDERLIST_CLIENT_ID
                }
                body_data = {
                    'revision': 0,
                }
                response = requests.delete(
                    'http://a.wunderlist.com/api/v1/webhooks/{0}'.format(
                        str(wh['id'])),
                    headers=headers, data=body_data)

    def download_to_stored_data(self, connection_object=None, plug=None,
                                task=None, **kwargs):
        if task is not None:
            task_id = task['subject']['id']
            q = StoredData.objects.filter(
                connection=connection_object.connection, plug=plug,
                object_id=task_id)
            task_stored_data = []
            if not q.exists():
                task_data = self.get_task(task_id)
                for k, v in task_data.items():
                    if type(v) not in [list, dict]:
                        task_stored_data.append(
                            StoredData(connection=connection_object.connection,
                                       plug=plug, object_id=task_id,
                                       name=k, value=v or ''))
            extra = {}
            for task in task_stored_data:
                try:
                    extra['status'] = 's'
                    extra = {'controller': 'wunderlist'}
                    task.save()
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            task.object_id, task.plug.id, task.connection.id),
                        extra=extra)
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s failed.' % (
                            task.object_id, task.plug.id, task.connection.id),
                        extra=extra)
            return True
        return False

    def get_target_fields(self, **kwargs):
        return [{'name': 'title', 'type': 'text', 'required': True},
                {'name': 'completed', 'type': 'text', 'required': True},
                {'name': 'completed_by_id', 'type': 'int', 'required': False},
                {'name': 'completed_at', 'type': 'text', 'required': False},
                {'name': 'created_at', 'type': 'text', 'required': True},
                {'name': 'parents', 'type': 'int', 'required': True}
                ]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.WunderList) for f in
                fields]

    def send_stored_data(self, source_data, target_fields, is_first=False):
        data_list = get_dict_with_source_data(source_data, target_fields)
        if self._plug is not None:
            obj_list = []
            extra = {'controller': 'WunderList'}
            for item in data_list:
                task = self.create_task(**item)
                if task.status_code in [200, 201]:
                    extra['status'] = 's'
                    self._log.info('Item: %s successfully sent.' % (
                        task.json()['data']['name']), extra=extra)
                    obj_list.append(task)
                else:
                    extra['status'] = 'f'
                    self._log.info('Item: failed to send.', extra=extra)
            return obj_list
        raise ControllerError("There's no plug")

    def do_webhook_process(self, body=None, POST=None, META=None, webhook_id=None, **kwargs):
        webhook= Webhook.objects.get(pk=webhook_id)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            action_name = webhook.plug.action.name
            if self.test_connection():
                if body['operation'] == 'create' and action_name == 'new task':
                    self.download_source_data(task=body)
                    webhook.plug.save()
                elif body['operation'] == 'update' and action_name == 'completed task':
                    if 'completed' in body['data'] and body['data']['completed'] == True:
                        self.download_source_data(task=body)
                        webhook.plug.save()
        return HttpResponse(status=200)

