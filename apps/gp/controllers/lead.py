from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.models import StoredData, ActionSpecification
from apiconnector.settings import FACEBOOK_APP_SECRET, FACEBOOK_APP_ID, FACEBOOK_GRAPH_VERSION
import facebook
import hashlib
import hmac
import httplib2
import json
import requests
from apiclient import discovery
from datetime import time
from oauth2client import client as GoogleClient
import surveymonty


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
        try:
            if self._plug is not None:
                # self._page = self._plug.plug_specification.all().get(action_specification__name__iexact='page')
                for s in self._plug.plug_specification.all():
                    if s.action_specification.name.lower() == 'page':
                        self._page = s.value
                    if s.action_specification.name.lower() == 'form':
                        self._form = s.value
        except:
            print("Error asignando los specifications")

    def test_connection(self):
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

    def get_action_specification_options(self, action_specification_id, **kwargs):
        action_specification = ActionSpecification.objects.filter(pk=action_specification_id)
        if action_specification.name.lower() == 'page':
            pages = self.get_pages(self._token)
            return tuple({'id': p['id'], 'name': p['name']} for p in pages)
        elif action_specification.name.lower() == 'form':
            forms = self.get_forms(self._token, kwargs.get('page_id', ''))
            return tuple({'id': p['id'], 'name': p['name']} for p in forms)
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


class SurveyMonkeyController(BaseController):
    _token = None
    _client = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        if args:
            super(SurveyMonkeyController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                    self._client = surveymonty.Client(self._token)
                    print(self._token)
                except Exception as e:
                    print("Error getting the surveymonkey token")
                    print(e)
        elif kwargs:
            host = kwargs.pop('token', None)
            self._client = surveymonty.Client(self._token)
        return self._token is not None and self._client is not None

    def get_survey_list(self):
        lista = self._client.get_surveys()
        return lista['data']

    def download_to_stored_data(self, connection_object, plug, client=None, responses=None):
        if plug is None:
            plug = self._plug
        if not self._client:
            return False

        if responses == None:
            responses = self.get_responses().__dict__["_content"].decode()
            responses = json.loads(responses)["data"]
        survey_id = self._plug.plug_specification.all()[0].value
        new_data = []
        for item in responses:
            response_id = item["id"]
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=response_id)
            if not q.exists():
                details = self.get_response_details(survey_id, response_id)
                for value in details:
                    if (value != "page_path" and value != "logic_path" and value != "metadata" and value != "custom_variables"):
                        new_data.append(StoredData(name=value, value=details[value], object_id=response_id,
                                                   connection=connection_object.connection, plug=plug))
        if new_data:
            extra = {'controller': 'surveymonkey'}
            for item in new_data:
                try:
                    self._log.info('Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                        item.object_id, item.plug.id, item.connection.id), extra=extra)
                    item.save()
                except:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
        return True

    def get_survey_details(self, survey_id):
        s = requests.Session()
        s.headers.update({
            "Authorization": "Bearer %s" % self._token,
            "Content-Type": "application/json"
        })
        url = "https://api.surveymonkey.net/v3/surveys/%s/details" % (survey_id)

        return s.get(url)

    def get_responses(self):
        survey_id = self._plug.plug_specification.all()[0].value
        s = requests.session()
        s.headers.update({
            "Authorization": "Bearer %s" % self._token,
            "Content-Type": "application/json"
        })

        url = "https://api.surveymonkey.net/v3/surveys/%s/responses" % (survey_id)
        return s.get(url)

    def get_response_details(self, survey_id, response_id):
        s = requests.session()
        s.headers.update({
            "Authorization": "Bearer %s" % self._token,
            "Content-Type": "application/json"
        })
        url = "https://api.surveymonkey.net/v3/surveys/%s/responses/%s" % (survey_id, response_id)
        # url = "https://api.surveymonkey.net/v3/collectors/%s/responses/%s/details" % (collector_id, response_id)
        data = s.get(url).__dict__
        data = data["_content"].decode()
        return json.loads(data)

    def get_list(self, survey_id):
        details = self.get_survey_details(survey_id).__dict__
        responses = self.get_responses(survey_id).__dict__['_content'].decode()
        responses = json.loads(responses)['data']
        list = []
        return list

    def create_webhook(self):
        survey_id = self._plug.plug_specification.all()[0].value
        survey_id = str(survey_id)
        plug_id = self._plug.plug_specification.all()[0].id
        print("plug_id")
        print(plug_id)
        redirect_uri = "https://l.grplug.com/wizard/surveymonkey/webhook/event/%s/" % (plug_id)
        s = requests.session()
        s.headers.update({
            "Authorization": "Bearer %s" % self._token,
            "Content-Type": "application/json"
        })
        payload = {
            "name": "Webhook_prueba",
            "event_type": "response_completed",
            "object_type": "survey",
            "object_ids": [survey_id],
            "subscription_url": redirect_uri
        }
        url = "https://api.surveymonkey.net/v3/webhooks"
        r = s.post(url, json=payload)
        if r.status_code == 201:
            print("Se creo el webhook survey monkey")
            return True
        return False
