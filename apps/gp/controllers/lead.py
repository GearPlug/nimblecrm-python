from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.models import StoredData, ActionSpecification, Webhook, PlugActionSpecification, Plug
from apps.gp.controllers.exceptions.facebookleads import FacebookLeadsError
from facebookmarketing.client import Client
from facebookmarketing.exception import UnknownError, InvalidOauth20AccessTokenError, BaseError
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from apiclient import discovery
from oauth2client import client as GoogleClient
import httplib2
import json
import requests
import time
import surveymonty


class GoogleFormsController(BaseController):
    _credential = None
    _spreadsheet_id = None

    def __init__(self, *args, **kwargs):
        BaseController.__init__(self, *args, **kwargs)

    def create_connection(self, *args, **kwargs):
        credentials_json = None
        if args:
            super(GoogleFormsController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    credentials_json = self._connection_object.credentials_json
                    if self._plug is not None:
                        try:
                            self._spreadsheet_id = self._plug.plug_action_specification.get(
                                action_specification__name__iexact='form').value
                        except Exception as e:
                            print("Error asignando los specifications GoogleForms 2")
                except Exception as e:
                    print("Error getting the GoogleForms attributes 1")
                    print(e)
                    credentials_json = None
        if credentials_json is not None:
            self._credential = GoogleClient.OAuth2Credentials.from_json(json.dumps(credentials_json))

    def test_connection(self):
        try:
            self._refresh_token()
            http_auth = self._credential.authorize(httplib2.Http())
            drive_service = discovery.build('drive', 'v3', http=http_auth)
            files = drive_service.files().list().execute()
        except Exception as e:
            print("Error Test connection GoogleForms")
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

    def get_action_specification_options(self, action_specification_id, **kwargs):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'form':
            return tuple({'id': p['id'], 'name': p['name']} for p in self.get_sheet_list())  # TODO SOLO CARGAR FORMS
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")


class FacebookLeadsController(BaseController):
    _token = None
    _page = None
    _form = None
    _client = None

    def __init__(self, *args):
        super(FacebookLeadsController, self).__init__(*args)

    def create_connection(self, *args, **kwargs):
        if args:
            super(FacebookLeadsController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    self._token = self._connection_object.token
                except AttributeError as e:
                    raise FacebookLeadsError(code=1,
                                             msg='Error getting the Facebook attributes args. {}'.format(str(e)))
            else:
                raise ControllerError('No connection.')
        try:
            if self._plug is not None:
                for s in self._plug.plug_action_specification.all():
                    if s.action_specification.name.lower() == 'page':
                        self._page = s.value
                    if s.action_specification.name.lower() == 'form':
                        self._form = s.value
        except Exception as e:
            raise FacebookLeadsError(code=1, msg='Error asignando los specifications. {}'.format(str(e)))
        try:
            self._client = Client(settings.FACEBOOK_APP_ID, settings.FACEBOOK_APP_SECRET, 'v2.10')
            self._client.set_access_token(self._token)
        except UnknownError as e:
            raise FacebookLeadsError(code=2, msg='Unknown error. {}'.format(str(e)))

    def test_connection(self):
        object_list = self.get_account()
        if 'id' in object_list:
            return True
        return False

    def extend_token(self, token):
        try:
            self._token = self._client.extend_token(token)['access_token']
            self._client.set_access_token(self._token)
            return self._token
        except BaseError as e:
            raise FacebookLeadsError(code=3, msg='Error. {}'.format(str(e)))

    def get_account(self):
        try:
            return self._client.get_account()
        except InvalidOauth20AccessTokenError as e:
            raise FacebookLeadsError(code=4, msg='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise FacebookLeadsError(code=3, msg='Error. {}'.format(str(e)))

    def get_pages(self):
        try:
            return self._client.get_pages()
        except InvalidOauth20AccessTokenError as e:
            raise FacebookLeadsError(code=4, msg='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise FacebookLeadsError(code=3, msg='Error. {}'.format(str(e)))

    def get_leads(self, form_id, from_date=None):
        try:
            return self._client.get_ad_leads(form_id, from_date)
        except InvalidOauth20AccessTokenError as e:
            raise FacebookLeadsError(code=4, msg='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise FacebookLeadsError(code=3, msg='Error. {}'.format(str(e)))

    def get_forms(self, page_id):
        try:
            return self._client.get_ad_account_leadgen_forms(page_id)
        except InvalidOauth20AccessTokenError as e:
            raise FacebookLeadsError(code=4, msg='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise FacebookLeadsError(code=3, msg='Error. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, from_date=None):
        if from_date is not None:
            from_date = int(time.mktime(from_date.timetuple()) * 1000)
        leads = self.get_leads(self._form, from_date=from_date)
        new_data = []
        leads = leads['data'] if leads else []
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
                except Exception as e:
                    extra['status'] = 'f'
                    self._log.info('Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                        item.object_id, item.name, item.plug.id, item.connection.id), extra=extra)
                    raise FacebookLeadsError(code=5, msg='Error in download to stored data. {}'.format(str(e)))
            return True
        return False

    def get_action_specification_options(self, action_specification_id, **kwargs):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'page':
            pages = self.get_pages()
            return tuple({'id': p['id'], 'name': p['name']} for p in pages['data'])
        elif action_specification.name.lower() == 'form':
            page_id = kwargs.get('page_id', '')[0] if isinstance(kwargs.get('page_id', ''), list) else kwargs.get(
                'page_id', '')
            forms = self.get_forms(page_id)
            return tuple({'id': p['id'], 'name': p['name']} for p in forms['data'])
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def create_webhook(self):
        current_page_id = PlugActionSpecification.objects.get(plug_id=self._plug.id,
                                                              action_specification__name='page').value
        try:
            token = self._client.get_page_token(current_page_id)
            if token is not None:
                app_token = self._client.get_app_token()
                self._client.create_app_subscriptions('page', settings.CURRENT_HOST + '/webhook/facebookleads/0/',
                                                      'leadgen', 'token-gearplug-058924', app_token['access_token'])
                self._client.create_page_subscribed_apps(current_page_id, token)
                return True
        except BaseError as e:
            raise FacebookLeadsError(code=3, msg='Error. {}'.format(str(e)))
        return False

    def do_webhook_process(self, body=None, GET=None, POST=None, **kwargs):
        response = HttpResponse(status=400)
        if GET is not None:
            verify_token = GET.get('hub.verify_token')
            challenge = GET.get('hub.challenge')
            if verify_token == 'token-gearplug-058924':
                response.status_code = 200
                response.content = challenge
        elif POST is not None:
            changes = body['entry'][0]['changes']
            for lead in changes:
                is_lead = lead['field'] == 'leadgen'
                if not is_lead:
                    continue
                form_id = lead['value']['form_id']
                lead_id = lead['value']['leadgen_id']
                created_time = lead['value']['created_time']
                plugs_to_update = Plug.objects.filter(Q(gear_source__is_active=True) | Q(is_tested=True),
                                                      action__name='get leads',
                                                      plug_action_specification__value=form_id)
                for plug in plugs_to_update:
                    self.create_connection(plug.connection.related_connection, plug)
                    if self.test_connection():
                        self.download_source_data(from_date=created_time)
                    if not plug.is_tested:
                        plug.is_tested = True
                        plug.save(update_fields=['is_tested', ])
            response.status_code = 200
        return response


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
                except Exception as e:
                    print("Error getting the surveymonkey token")
                    print(e)
        elif kwargs:
            host = kwargs.pop('token', None)
            self._client = surveymonty.Client(self._token)
        return self._token is not None and self._client is not None

    def test_connection(self):
        try:
            self._client = surveymonty.Client(self._token)
            return self._token is not None
        except Exception as e:
            print("error survey monkey test connection")
            print(e)
            return None

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
        survey_id = self._plug.plug_action_specification.all()[0].value
        new_data = []
        for item in responses:
            response_id = item["id"]
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=response_id)
            if not q.exists():
                details = self.get_response_details(survey_id, response_id)
                for value in details:
                    if (
                                            value != "page_path" and value != "logic_path" and value != "metadata" and value != "custom_variables"):
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
        survey_id = self._plug.plug_action_specification.all()[0].value
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
        action = self._plug.action.name
        if action == "read a survey":
            survey_id = self._plug.plug_action_specification.all()[0].value
            survey_id = str(survey_id)
            webhook = Webhook.objects.create(name='surveymonkey', plug=self._plug,
                                             url='')
            plug_id = self._plug.plug_action_specification.all()[0].id
            redirect_uri = "%s/webhook/surveymonkey/%s/" % settings.CURRENT_HOST, webhook.id
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
                webhook.url = redirect_uri
                webhook.generated_id = r.json()["id"]
                webhook.is_active = True
                webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True
        return False

    def get_action_specification_options(self, action_specification_id, **kwargs):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'survey':
            return [{'name': o['title'], 'id': o['id']} for o in self.get_survey_list()]
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def do_webhook_process(self, body=None, POST=None, **kwargs):
        responses = []
        survey = {'id': body['object_id']}
        responses.append(survey)
        survey_list = PlugActionSpecification.objects.filter(
            action_specification__action__action_type='source',
            action_specification__action__connector__name__iexact="SurveyMonkey",
            value=body['resources']['survey_id']
        )
        for survey in survey_list:
            self._connection_object, self._plug = survey.plug.connection.related_connection, survey.plug
            if self.test_connection():
                self.download_source_data(event=body)
        return HttpResponse(status=200)
