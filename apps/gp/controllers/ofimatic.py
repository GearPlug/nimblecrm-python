from apps.gp.controllers.base import BaseController, GoogleBaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import StoredData, ActionSpecification, Webhook, PlugActionSpecification, Plug
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
        super(GoogleSpreadSheetsController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                credentials_json = self._connection_object.credentials_json
            except Exception as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.GoogleSpreadSheets.name,
                                      message='The attributes necessary to make the connection were not obtained {}'.format(
                                          str(e)))
            try:
                self._credential = GoogleClient.OAuth2Credentials.from_json(json.dumps(credentials_json))
            except Exception as e:
                raise ControllerError(code=1003, controller=ConnectorEnum.GoogleSpreadSheets.name,
                                      message='Error in the instantiation of the client.. {}'.format(str(e)))
            try:
                self._spreadsheet_id = self._plug.plug_action_specification.get(
                    action_specification__name__iexact='spreadsheet').value
                self._worksheet_name = self._plug.plug_action_specification.get(
                    action_specification__name__iexact='worksheet').value
            except Exception as e:
                raise ControllerError(code=1005, controller=ConnectorEnum.GoogleSpreadSheets,
                                      message='Error while choosing specifications. {}'.format(str(e)))

    def test_connection(self):
        try:
            self._refresh_token()
            http_auth = self._credential.authorize(httplib2.Http())
            drive_service = discovery.build('drive', 'v3', http=http_auth)
            files = drive_service.files().list().execute()
        except GoogleClient.HttpAccessTokenRefreshError:
            # raise ControllerError(code=1004, controller=ConnectorEnum.GoogleSpreadSheets.name,
            # message='Error in the connection test... {}'.format(str(e)))
            self._report_broken_token()
            return False
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.GoogleSpreadSheets.name,
            # message='Error in the connection test... {}'.format(str(e)))
            return False
        if files and isinstance(files, dict) and 'files' in files:
            return True
        return False

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, **kwargs):
        if not self._spreadsheet_id or not self._worksheet_name:
            return False
        data = self.get_worksheet_values()
        raw_data = []
        new_data = []
        for idx, item in enumerate(data[1:], 1):
            unique_value = idx
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=unique_value)
            if not q.exists():
                item_data = []
                item_raw = {}
                for idx2, cell in enumerate(item):
                    item_data.append(StoredData(name=data[0][idx2], value=cell, object_id=unique_value,
                                                connection=connection_object.connection, plug=plug))
                    _dict = {data[0][idx2]: cell}
                    item_raw.update(_dict)

                new_data.append(item_data)
                item_raw['id'] = idx
                raw_data.append(item_raw)
        # Nueva forma
        if new_data:
            result_list = []
            for item in new_data:
                for stored_data in item:
                    try:
                        stored_data.save()
                    except Exception as e:
                        is_stored = False
                        break
                    is_stored = True
                obj_raw = "ROW DATA NOT FOUND."
                for obj in raw_data:
                    if stored_data.object_id == obj['id']:
                        obj_raw = obj
                        break
                raw_data.remove(obj_raw)
                result_list.append({'identifier': {'name': 'id', 'value': stored_data.object_id},
                                    'is_stored': is_stored, 'raw': obj_raw, })
            return {'downloaded_data': result_list, 'last_source_record': result_list[-1]['identifier']['value']}
        return False

    def send_stored_data(self, data_list, **kwargs):
        obj_list = []
        _list = []
        if self._plug is not None:
            for obj in data_list:
                l = [val for val in obj.values()]
                _list.append({'obj': obj, 'list': l})
            sheet_values = self.get_worksheet_values()
            for idx, item in enumerate(_list, len(sheet_values) + 1):
                obj_result = {'data': dict(item['obj'])}
                try:
                    res = self.create_row(item['list'], idx)
                    obj_result['response'] = res
                    obj_result['sent'] = True
                    obj_result['identifier'] = res['updatedRange'].split('!')[-1]
                except Exception as e:
                    obj_result['response'] = 'Error writing row'
                    obj_result['sent'] = False
                    obj_result['identifier'] = None
                obj_list.append(obj_result)
            return obj_list

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
        files = drive_service.files().list(q="mimeType='application/vnd.google-apps.spreadsheet'",
                                           spaces='drive').execute()
        sheet_list = tuple(f for f in files['files'])
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
        GoogleBaseController.__init__(self, connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(GoogleCalendarController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                credentials_json = self._connection_object.credentials_json
            except Exception as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.GoogleCalendar.name,
                                      message='The attributes necessary to make the connection were not obtained {}'.format(
                                          str(e)))
            try:
                self._credential = GoogleClient.OAuth2Credentials.from_json(json.dumps(credentials_json))
                http_auth = self._credential.authorize(httplib2.Http())
                self._connection = discovery.build('calendar', 'v3', http=http_auth)
            except Exception as e:
                raise ControllerError(code=1003, controller=ConnectorEnum.GoogleCalendar.name,
                                      message='Error in the instantiation of the client.. {}'.format(str(e)))

    def test_connection(self):
        try:
            self._refresh_token()
            calendars = self._connection.calendarList().list().execute()
        except GoogleClient.HttpAccessTokenRefreshError:
            # raise ControllerError(code=1004, controller=ConnectorEnum.GoogleCalendar.name,
            # message='Error in the connection test... {}'.format(str(e)))
            self._report_broken_token()
            return False
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.GoogleCalendar.name,
            # message='Error in the connection test... {}'.format(str(e)))
            return False
        if calendars and isinstance(calendars, dict) and 'items' in calendars:
            return True
        return False

    def download_to_stored_data(self, connection_object=None, plug=None, events=None, **kwargs):
        if events is None:
            return False
        new_data = []
        raw_data = []
        for event in events:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=event['id'])
            if not q.exists():
                item_data = []
                for k, v in event.items():
                    item_data.append(
                        StoredData(connection=connection_object.connection, plug=plug, object_id=event['id'], name=k,
                                   value=v or ''))

                new_data.append(item_data)
                raw_data.append(event)
        is_stored = False
        result_list = []
        for item in new_data:
            for stored_data in item:
                try:
                    stored_data.save()
                    is_stored = True
                except Exception as e:
                    print(e)
            for obj in raw_data:
                if stored_data.object_id == obj['id']:
                    obj_raw = obj
                    break
            result_list.append(
                {'raw': obj_raw, 'is_stored': is_stored, 'identifier': {'name': 'id', 'value': stored_data.object_id}})
        return {'downloaded_data': result_list, 'last_source_record': result_list[-1]['identifier']['value']}

    def send_stored_data(self, data_list, is_first=False):
        result_list = []
        if self._plug is not None:
            for obj in data_list:
                try:
                    _result = self.create_issue(self._plug.plug_action_specification.all()[0].value, obj)
                    identifier = _result['id']
                    _sent = True
                except Exception as e:
                    _result = str(e)
                    identifier = '-1'
                    _sent = False
                result_list.append({'data': dict(obj), 'response': _result, 'sent': _sent, 'identifier': identifier})
        return result_list

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
        return self._connection.events().insert(calendarId=calendar_id, body=event).execute()

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
        url = 'https://www.googleapis.com/calendar/v3/calendars/{}/events/watch'.format(calendar_id)
        webhook = Webhook.objects.create(name='googlecalendar', plug=self._plug, url='')
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
        calendar_id = self._plug.plug_action_specification.get(action_specification__name__iexact='calendar').value
        eventsResult = self._connection.events().list(calendarId=calendar_id, maxResults=limit, singleEvents=True,
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
        return [MapField(f, controller=ConnectorEnum.GoogleCalendar) for f in fields]

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        calendar_list = self._connection.calendarList().list().execute()
        if action_specification.name.lower() == "calendar":
            return tuple({"name": c["summary"], "id": c["id"]} for c in calendar_list['items'])
        else:
            raise ControllerError(
                "That specification doesn't belong to an action in this connector.")

    def do_webhook_process(self, body=None, POST=None, META=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
        if webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            if self.test_connection():
                events = self.get_events()
                self.download_source_data(events=events)
                webhook.plug.save()
        return HttpResponse(status=200)

    @property
    def has_webhook(self):
        return True


class EvernoteController(BaseController):
    _token = None
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(EvernoteController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(EvernoteController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
            except Exception as e:
                raise ControllerError(code=1001, controller=ConnectorEnum.Evernote,
                                      message='Error getting the attributes args. {}'.format(str(e)))
            try:
                self._client = EvernoteClient(token=self._token)
            except Exception as e:
                raise ControllerError(code=1003, controller=ConnectorEnum.Evernote,
                                      message='Error in the instantiation of the client.. {}'.format(str(e)))

    def test_connection(self):
        try:
            response = self._client.get_note_store()
            data = response.__dict__
        except Exception as e:
            # raise ControllerError(code=1004, controller=ConnectorEnum.Evernote,
            #                       message='Error in the connection test.. {}'.format(str(e)))
            return False
        if data is not None and isinstance(data, dict) and 'error' not in data and '_client' in data:
            return True
        else:
            return False

    def download_to_stored_data(self, connection_object=None, plug=None, **kwargs):
        notes = self.get_notes(self._token)
        new_data = []
        for item in notes:
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=item['id'])
            if not q.exists():
                new_item = [(
                    StoredData(name=column, value=item[column], object_id=item['id'],
                               connection=connection_object.connection, plug=plug)) for column in item]
                new_data.append(new_item)
        downloaded_data = []
        for item in new_data:
            history_obj = {'identifier': None, 'is_stored': False, 'raw': {}}
            for field in item:
                field.save()
                history_obj['raw'][field.name] = field.value
                history_obj['is_stored'] = True
            history_obj['identifier'] = {'name': 'id', 'value': field.object_id}
            downloaded_data.append(history_obj)
        if downloaded_data:
            return {'downloaded_data': downloaded_data, 'last_source_record': downloaded_data[0]['raw']['id']}
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

    def send_stored_data(self, data_list, *args, **kwargs):
        obj_list = []
        for item in data_list:
            try:
                obj_result = {'data': item['data']}
                result = self.create_note(item)
                data = result.__dict__
                obj_result['response'] = data
                obj_result['identifier'] = data['guid']
                obj_result['sent'] = True
            except Exception as e:
                obj_result['response'] = str(e)
                obj_result['identifier'] = '-1'
                obj_result['sent'] = False
            obj_list.append(obj_result)
        return obj_list

    def create_note(self, data):
        _title = data['data']['title']
        _content = data['data']['content']
        client = EvernoteClient(token=self._token)
        noteStore = client.get_note_store()
        note = Types.Note()
        note.title = _title
        note.content = '<?xml version="1.0" encoding="UTF-8"?><!DOCTYPE en-note SYSTEM "http://xml.evernote.com/pub/enml2.dtd">'
        note.content += '<en-note>' + _content + '</en-note>'
        return noteStore.createNote(note)

    def delete_note(self):
        # TODO: realizar metodo.
        """
        :return:
        """
        pass


class WunderListController(BaseController):
    _token = None
    _api = wunderpy2.WunderApi()
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        super(WunderListController, self).__init__(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(WunderListController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
            except Exception as e:
                raise ControllerError(
                    code=1001,
                    controller=ConnectorEnum.WunderList,
                    message='The attributes necessary to make the connection were not obtained. {}'.format(str(e)))
            try:
                self._client = self._api.get_client(self._token, settings.WUNDERLIST_CLIENT_ID)
            except Exception as e:
                raise ControllerError(
                    code=1003,
                    controller=ConnectorEnum.WunderList,
                    message='Error in the instantiation of the client.. {}'.format(str(e)))

    def test_connection(self):
        try:
            response = self.get_lists()
        except Exception as e:
            # raise ControllerError(
            #     code=1004,
            #     controller=ConnectorEnum.WunderList,
            #     message='Error in the connection test. {}'.format(str(e)))
            return False
        if response is not None and isinstance(response, list) and isinstance(response[0], dict) and 'id' in response[
            0]:
            return True
        else:
            return False

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
        _id = kwargs['assignee_id']
        json_acceptable_string = _id.replace("'", '"')
        _id = int(json.loads(json_acceptable_string)['id'])
        kwargs['assignee_id'] = _id
        kwargs['list_id'] = int(self._plug.plug_action_specification.get(action_specification__name='list').value)
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain',
                   'X-Access-Token': self._token,
                   'X-Client-ID': settings.WUNDERLIST_CLIENT_ID}
        response = requests.post('http://a.wunderlist.com/api/v1/tasks',
                                 data=json.dumps(kwargs), headers=headers)
        return response

    def delete_task(self, task_id):
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain',
                   'X-Access-Token': self._token,
                   'X-Client-ID': settings.WUNDERLIST_CLIENT_ID}
        data = {'revision': 1}
        response = requests.delete('http://a.wunderlist.com/api/v1/tasks/{0}'.format(task_id),
                                   params=data, headers=headers)
        return response.status_code

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

    def view_webhooks(self, list_id):
        headers = {
            'X-Access-Token': self._token,
            'X-Client-ID': settings.WUNDERLIST_CLIENT_ID
        }
        body_data = {
            'list_id': str(list_id),
        }
        response = requests.get(
            'http://a.wunderlist.com/api/v1/webhooks', headers=headers,
            data=body_data)
        return response.json()

    # Metodo de borrado de webhooks, utilizacion manual.
    def delete_webhook(self, id_webhook):
        headers = {
            'X-Access-Token': self._token,
            'X-Client-ID': settings.WUNDERLIST_CLIENT_ID
        }
        body_data = {
            'revision': 0,
        }
        response = requests.delete(
            'http://a.wunderlist.com/api/v1/webhooks/{0}'.format(str(id_webhook)),
            headers=headers, data=body_data)
        return response

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
            result_list = []
            for taskk in task_stored_data:
                try:
                    taskk.save()
                    is_stored = True
                    last_object_id = task_id
                except Exception as e:
                    is_stored = False
                    last_object_id = ""
                result_list = [
                    {'raw': task, 'is_stored': is_stored, 'identifier': {'name': 'id', 'value': last_object_id}}]
            return {'downloaded_data': result_list, 'last_source_record': last_object_id}

    def get_target_fields(self, **kwargs):
        users = self.get_users()
        return [{'name': 'title', 'type': 'text', 'required': True, 'label': 'Title'},
                {"name": "assignee_id", "required": False, "type": 'varchar',
                 "choices": users, 'label': 'Assignee'},
                ]

    def get_mapping_fields(self, **kwargs):
        fields = self.get_target_fields()
        return [MapField(f, controller=ConnectorEnum.WunderList) for f in
                fields]

    def send_stored_data(self, data_list):
        result_list = []
        for item in data_list:
            task = self.create_task(**item)
            if task.status_code in [200, 201]:
                sent = True
                identifier = task.json()['id']
            else:
                sent = False
                identifier = ""
            result_list.append({'data': dict(item), 'response': "", 'sent': sent, 'identifier': identifier})
        return result_list

    def do_webhook_process(self, body=None, POST=None, META=None, webhook_id=None, **kwargs):
        webhook = Webhook.objects.get(pk=webhook_id)
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

    @property
    def has_webhook(self):
        return True

    def get_users(self):
        headers = {
            'Content-type': 'application/json', 'Accept': 'text/plain',
            'X-Access-Token': self._token,
            'X-Client-ID': settings.WUNDERLIST_CLIENT_ID
        }
        response = requests.get(
            'http://a.wunderlist.com/api/v1/users', headers=headers)
        # 03/01/2018 - Se modifico de tal manera que si no hay 'name' se obvie ese usuario.
        return [{'name': r['name'], 'id': r['id']} for r in response.json() if 'name' in r]
