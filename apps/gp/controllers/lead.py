from apps.gp.controllers.base import BaseController, GoogleBaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.models import StoredData, ActionSpecification, Webhook, \
    PlugActionSpecification, Plug
from apps.gp.enum import ConnectorEnum
from facebookmarketing.client import Client
from facebookmarketing.exceptions import UnknownError, \
    InvalidOauth20AccessTokenError, BaseError
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from apiclient import discovery
from oauth2client import client as GoogleClient
import httplib2
import json
import requests
import surveymonty
from typeform.client import Client as TypeformClient
from dateutil.parser import parse


class GoogleFormsController(GoogleBaseController):
    _credential = None
    _spreadsheet_id = None

    def __init__(self, connection=None, plug=None, **kwargs):
        GoogleBaseController.__init__(self, connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(GoogleFormsController, self).create_connection(connection=connection, plug=plug)
        credentials_json = None
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
        if credentials_json is not None:
            self._credential = GoogleClient.OAuth2Credentials.from_json(json.dumps(credentials_json))

    def test_connection(self):
        try:
            self._refresh_token()
            http_auth = self._credential.authorize(httplib2.Http())
            drive_service = discovery.build('drive', 'v3', http=http_auth)
            files = drive_service.files().list().execute()
        except GoogleClient.HttpAccessTokenRefreshError:
            files = None
            self._report_broken_token()
        except Exception as e:
            print("Error Test GoogleForms. Message: {}".format(str(e)))
            files = None
        return files is not None

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, **kwargs):
        if not self._spreadsheet_id:
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
    """
        Facebook Marketing - Leads
        REQUIRES: FacebookMarketing-Python Library owned by GearPlug.
        URL: https://github.com/GearPlug/facebookmarketing-python

        TODO:
        - REVISAR WEBHOOK
        - REVISAR field from_date en download to stored_data (no webhook)
    """

    _token = None
    _page = None
    _form = None
    _client = None

    def __init__(self, connection=None, plug=None):
        super(FacebookLeadsController, self).__init__(connection=connection,
                                                      plug=plug)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(FacebookLeadsController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
            except AttributeError as e:
                raise ControllerError(code=1, controller=ConnectorEnum.FacebookLeads,
                                      message='Failed to get the token. \n{}'.format(str(e)))
            try:

                self._client = Client(settings.FACEBOOK_APP_ID, settings.FACEBOOK_APP_SECRET, 'v2.10')
                self._client.set_access_token(self._token)
            except UnknownError as e:
                raise ControllerError(code=2, controller=ConnectorEnum.FacebookLeads,
                                      message='Unknown error. {}'.format(str(e)))
            try:
                if self._plug is not None:
                    self._page = self._plug.plug_action_specification.filter(
                        action_specification__name='page').first().value
                    self._form = self._plug.plug_action_specification.filter(
                        action_specification__name='form').first().value
            except Exception as e:
                raise ControllerError(code=1, controller=ConnectorEnum.FacebookLeads,
                                      message='Error asignando los specifications. {}'.format(str(e)))

    def test_connection(self):
        try:
            object_list = self.get_account()
            if 'id' in object_list:
                result = True
        except Exception as e:
            print("error testing the connection\nMessage:{0}".format(str(e)))
            result = False
        return result

    def extend_token(self, token):
        try:
            if self._client is None:
                self._client = Client(settings.FACEBOOK_APP_ID, settings.FACEBOOK_APP_SECRET, 'v2.10')
            self._token = self._client.extend_token(token)['access_token']
            self._client.set_access_token(self._token)
            return self._token
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.FacebookLeads, message='Error. {}'.format(str(e)))

    def get_account(self):
        try:
            return self._client.get_account()
        except InvalidOauth20AccessTokenError as e:
            raise ControllerError(code=4, controller=ConnectorEnum.FacebookLeads,
                                  message='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise
            raise ControllerError(code=3, controller=ConnectorEnum.FacebookLeads, message='Error. {}'.format(str(e)))

    def get_pages(self):
        try:
            return self._client.get_pages()
        except InvalidOauth20AccessTokenError as e:
            raise ControllerError(code=4, controller=ConnectorEnum.FacebookLeads,
                                  message='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.FacebookLeads, message='Error. {}'.format(str(e)))

    def get_leads(self, form_id, from_date=None):
        try:
            return self._client.get_ad_leads(form_id, from_date)
        except InvalidOauth20AccessTokenError as e:
            raise ControllerError(code=4, controller=ConnectorEnum.FacebookLeads,
                                  message='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise
            raise ControllerError(code=3, controller=ConnectorEnum.FacebookLeads, message='Error. {}'.format(str(e)))

    def get_leadgen(self, leadgen_id):
        try:
            print("get lead")
            return self._client.get_leadgen(leadgen_id)
        except Exception as e:
            raise

    def get_forms(self, page_id):
        try:
            return self._client.get_ad_account_leadgen_forms(page_id)
        except InvalidOauth20AccessTokenError as e:
            raise ControllerError(code=4, controller=ConnectorEnum.FacebookLeads,
                                  message='Invalid Token. {}'.format(str(e)))
        except BaseError as e:
            raise ControllerError(code=3, controller=ConnectorEnum.FacebookLeads, message='Error. {}'.format(str(e)))

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, lead=None, from_date=None,
                                **kwargs):
        """
                :param connection_object:
                :param plug:
                :param last_source_record: IF the value is not None the download will ask for data after the value  recived.
                :param limit:
                :param kwargs:  ????  #TODO: CHECK
                :return:
                """
        if lead is not None:
            aditional_data = {
                'page_id': lead['value']['page_id'],
                'form_id': lead['value']['form_id'],
            }
            leadgen_id = lead['value']['leadgen_id']
            if 'adgroup_id' in lead['value']:
                aditional_data['adgroup_id'] = lead['value']['adgroup_id']
            data = [self.get_leadgen(leadgen_id)]
        else:
            try:
                data = self.get_leads(self._form, from_date=from_date)['data']
            except IndexError:
                raise
                return False
            aditional_data = {
                'page_id': self._page,
                'form_id': self._form,
            }
        new_leads = []
        raw_data = []
        for lead in data:
            leadgen_id = lead['id']
            new_lead = []
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=leadgen_id)
            if not q.exists():
                aditional_data['created_time'] = lead['created_time']
                aditional_data['created_time_timestamp'] = parse(lead['created_time']).timestamp()
                aditional_data['leadgen_id'] = lead['id']
                print(lead)
                obj_raw = {d['name']: d['values'][0] if isinstance(d['values'], list) else d['values']
                           for d in lead['field_data']}
                obj_raw.update(aditional_data)
                raw_data.append(obj_raw)
                for d in raw_data:
                    for k, v in d.items():
                        new_lead.append(StoredData(name=k, value=v or '', object_id=leadgen_id,
                                                   connection=connection_object.connection, plug=plug))
                    new_leads.append(new_lead)
        if new_leads:
            leads_result = []
            for new_lead in new_leads:
                for stored_data in new_lead:
                    try:
                        stored_data.save()
                        is_stored = True
                    except Exception as e:
                        is_stored = False
                for lead in raw_data:
                    # TODO: Corregir
                    if stored_data.object_id == lead['leadgen_id']:
                        leads_result.append(
                            {'identifier': {'name': 'leadgen_id', 'value': lead['leadgen_id']}, 'raw': lead,
                             'is_stored': is_stored})
                        break
                        # data.remove(lead)
            obj_last_source_record = leads_result[-1]['raw']['created_time_timestamp']
            return {'downloaded_data': leads_result, 'last_source_record': obj_last_source_record}
        return False

    def _save_row(self, item):  # TODO: ASYNC METHOD
        try:
            for stored_data in item:
                stored_data.save()
            return True, stored_data.object_id
        except Exception as e:
            return False, item[0].object_id

    def _get_insert_statement(self, item):
        return """INSERT INTO `{0}`({1}) VALUES ({2})""".format(self._table, ",".join(item.keys()),
                                                                ",".join('\"{0}\"'.format(i) for i in item.values()))

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

    def create_webhook(self, url=settings.WEBHOOK_HOST):
        current_page_id = PlugActionSpecification.objects.get(plug_id=self._plug.id,
                                                              action_specification__name='page').value
        try:
            token = self._client.get_page_token(current_page_id)
            if token is not None:
                app_token = self._client.get_app_token()
                webhook = Webhook.objects.create(name='facebookleads', plug=self._plug, url='', is_deleted=True)
                self._client.create_app_subscriptions('page', '{0}/webhook/facebookleads/0/'.format(url), 'leadgen',
                                                      'token-gearplug-058924', app_token['access_token'])
                self._client.create_page_subscribed_apps(current_page_id, token)
                webhook.url = '{0}/webhook/facebookleads/0/'.format(url)
                webhook.is_active = True
                webhook.is_deleted = False
                webhook.save(update_fields=['url', 'is_active', 'is_deleted'])
                return True
        except BaseError as e:
            raise
            raise ControllerError(code=3, message='Error. {}'.format(str(e)))
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
                page_id = lead['value']['page_id']
                plugs_to_update = Plug.objects.filter(
                    Q(gear_source__is_active=True) | Q(is_tested=False),
                    plug_action_specification__value__iexact=form_id,
                    plug_action_specification__action_specification__name__iexact='form',
                    action__name='get leads', )
                plugs_to_update = plugs_to_update.filter(
                    plug_action_specification__value__iexact=page_id,
                    plug_action_specification__action_specification__name__iexact='page')
                for plug in plugs_to_update:
                    try:
                        self.create_connection(connection=plug.connection.related_connection, plug=plug)
                        if self.test_connection():
                            last_source_record = self.download_source_data(lead=lead)
                            if last_source_record:
                                self._plug.gear_source.first().gear_map.last_source_order_by_field_value = last_source_record
                                self._plug.gear_source.first().gear_map.save(
                                    update_fields=['last_source_order_by_field_value'])
                    except Exception as e:
                        raise e
                        print("ERROR: {0}".format(e))
                    if not plug.is_tested:
                        plug.is_tested = True
                        plug.save(update_fields=['is_tested', ])
            response.status_code = 200
        return response

    def has_webhook(self):
        return True


class SurveyMonkeyController(BaseController):
    _token = None
    _client = None

    def __init__(self, connection=None, plug=None):
        BaseController.__init__(self, connection=connection, plug=plug)

    def create_connection(self, connection=None, plug=None):
        super(SurveyMonkeyController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._token = self._connection_object.token
                self._client = surveymonty.Client(self._token)
            except Exception as e:
                print("Error getting the surveymonkey token")
                print(e)

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

    def download_to_stored_data(self, connection_object, plug, client=None,
                                response=None):
        # Codigo para traer historial de respuestas
        # if responses == None:
        #     responses = self.get_responses().__dict__["_content"].decode()
        #     responses = json.loads(responses)["data"]

        survey_id = response['resources']['survey_id']
        new_data = []
        response_id = response["object_id"]
        q = StoredData.objects.filter(
            connection=connection_object.connection, plug=plug,
            object_id=response_id)
        if not q.exists():
            details = self.get_response_details(survey_id, response_id)
            for value in details:
                if (
                                        value != "page_path" and value != "logic_path" and value != "metadata" and value != "custom_variables"):
                    new_data.append(
                        StoredData(name=value, value=details[value],
                                   object_id=response_id,
                                   connection=connection_object.connection,
                                   plug=plug))
        if new_data:
            extra = {'controller': 'surveymonkey'}
            for item in new_data:
                try:
                    self._log.info(
                        'Item ID: %s, Connection: %s, Plug: %s successfully stored.' % (
                            item.object_id, item.plug.id, item.connection.id),
                        extra=extra)
                    item.save()
                except:
                    extra['status'] = 'f'
                    self._log.info(
                        'Item ID: %s, Field: %s, Connection: %s, Plug: %s failed to save.' % (
                            item.object_id, item.name, item.plug.id,
                            item.connection.id), extra=extra)
        return True

    def get_survey_details(self, survey_id):
        s = requests.Session()
        s.headers.update({
            "Authorization": "Bearer %s" % self._token,
            "Content-Type": "application/json"
        })
        url = "https://api.surveymonkey.net/v3/surveys/%s/details" % (
            survey_id)

        return s.get(url)

    def get_responses(self):
        survey_id = self._plug.plug_action_specification.all()[0].value
        s = requests.session()
        s.headers.update({
            "Authorization": "Bearer %s" % self._token,
            "Content-Type": "application/json"
        })

        url = "https://api.surveymonkey.net/v3/surveys/%s/responses" % (
            survey_id)
        return s.get(url)

    def get_response_details(self, survey_id, response_id):
        s = requests.session()
        s.headers.update({
            "Authorization": "Bearer %s" % self._token,
            "Content-Type": "application/json"
        })
        url = "https://api.surveymonkey.net/v3/surveys/%s/responses/%s" % (
            survey_id, response_id)
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
            survey_id = self._plug.plug_action_specification.get(action_specification__name='survey')
            webhook = Webhook.objects.create(name='surveymonkey',
                                             plug=self._plug, url='')

            redirect_uri = "{0}/webhook/surveymonkey/{1}/".format(settings.CURRENT_HOST, webhook.id)
            s = requests.session()
            s.headers.update({
                "Authorization": "Bearer %s" % self._token,
                "Content-Type": "application/json"
            })
            payload = {
                "name": "Webhook_survey",
                "event_type": "response_completed",
                "object_type": "survey",
                "object_ids": [survey_id.value],
                "subscription_url": redirect_uri
            }
            url = "https://api.surveymonkey.net/v3/webhooks"
            r = s.post(url, json=payload)
            if r.status_code == 201:
                webhook.url = redirect_uri
                webhook.generated_id = r.json()["id"]
                webhook.is_active = True
                webhook.save(
                    update_fields=['url', 'generated_id', 'is_active'])
            else:
                webhook.is_deleted = True
                webhook.save(update_fields=['is_deleted', ])
            return True
        return False

    def get_action_specification_options(self, action_specification_id,
                                         **kwargs):
        action_specification = ActionSpecification.objects.get(
            pk=action_specification_id)
        if action_specification.name.lower() == 'survey':
            return [{'name': o['title'], 'id': o['id']} for o in
                    self.get_survey_list()]
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
                self.download_source_data(response=body)
                webhook.plug.save()
        return HttpResponse(status=200)

    def has_webhook(self):
        return True


class TypeFormController(BaseController):
    _client = None

    def __init__(self, connection=None, plug=None, **kwargs):
        BaseController.__init__(self, connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None, **kwargs):
        super(TypeFormController, self).create_connection(connection=connection, plug=plug)
        if self._connection_object is not None:
            try:
                self._client = TypeformClient(self._connection_object.api_key)
            except Exception as e:
                print("Error getting the Typeform attributes")
                self._client = None

    def test_connection(self):
        try:
            self._client = TypeformClient(self._connection_object.api_key)
            return self._client is not None
        except Exception as e:
            print("error Typeform test connection")
            print(e)
            return False

    def create_webhook(self):
        print("create webhook")
        token = "9QarwArtUyLtvv3fNuUoytjU7uMPuxKJu4TDnbxw1onY"
        action = self._plug.action.name
        if action.lower() == 'new answer':
            # creación de webhook
            webhook = Webhook.objects.create(name='typeform', plug=self._plug, url='', expiration='')
            url_base = settings.WEBHOOK_HOST
            url_path = reverse('home:webhook', kwargs={'connector': 'typeform', 'webhook_id': webhook.id})
            webhook.url = url_base + url_path
            webhook.generated_id = webhook.id
            webhook.is_active = True  # Cambiar a False
            webhook.save(update_fields=['url', 'generated_id', 'is_active'])
            url_base = settings.WEBHOOK_HOST
            url_path = reverse('home:webhook',
                               kwargs={'connector': 'typeform',
                                       'webhook_id': webhook.id})
            #Código para crear el webhook, funciona con API
            headers = {
                'Authorization': 'bearer {0}'.format(token),
                'Content-Type': 'application/json',
            }
            data = {
                'url': url_base + url_path,
                'enabled': True,
            }
            form_id = self._plug.plug_action_specification.get(action_specification__name='form')
            _urr_webhook ='https://api.typeform.com/forms/{0}/webhooks/{1}'.format(form_id.value, webhook.id)
            print("url webhook", _urr_webhook)
            response = requests.put(_urr_webhook, headers=headers, data=json.dumps(data))
            print("response", response.text)
            print(response.status_code)
            return True
        return False

    def do_webhook_process(self, body=None, GET=None, POST=None, META=None, webhook_id=None, **kwargs):
        print("body", body)
        print("post", POST)
        webhook = Webhook.objects.filter(pk=webhook_id).prefetch_related('plug').first()
        if not webhook.plug.gear_source.first().is_active or not webhook.plug.is_tested:
            if not webhook.plug.is_tested:
                webhook.plug.is_tested = True
                webhook.plug.save()
            self.create_connection(connection=webhook.plug.connection.related_connection, plug=webhook.plug)
            try:
                PlugActionSpecification.objects.get(action_specification__name__iexact='form', plug=webhook.plug,
                                                    value=body['form_response']['form_id'])
                if self.test_connection():
                    self.download_source_data()
            except PlugActionSpecification.DoesNotExist:
                print("The webhook {0} is not listening to the form {1}.".format(webhook_id,
                                                                                 body['form_response']['form_id']))
                return HttpResponse(status=403)
        return HttpResponse(status=200)

    def download_to_stored_data(self, connection_object, plug, last_source_record=None, answer=None, **kwargs):
        print("download to stored data")
        # import pprint
        # pprint.pprint(answer)
        form = self._plug.plug_action_specification.get(action_specification__name__iexact='form')
        list_data_answers = []
        if answer is not None:
            if 'event_type' in answer and answer['event_type'] == 'form_response':
                data_questions = {question['id']: question['title'] for question in
                                  answer['form_response']['definition']['fields']}
                obj_raw = {'completed': '1', 'token': answer['form_response']['token'],
                           'submitted_at': answer['form_response']['submitted_at'], }
                for raw_answer in answer['form_response']['answers']:
                    type = raw_answer['type']
                    if type == 'choice':
                        value = raw_answer[type]['label']
                    elif type == 'boolean':
                        value = '1' if type == True else '0'
                    else:
                        value = str(raw_answer[type])
                    obj_raw[data_questions[raw_answer['field']['id']]] = value
                list_data_answers.append(obj_raw)
        else:
            print("sin webhook")
            form_data = self._client.get_form_information(form.value)
            data_questions = self._client.get_form_questions(form=form_data)
            data_answers = self._client.get_form_metadata(form=form_data)
            dict_data_questions = {question['id']: question['question'] for question in data_questions}
            print("aQ", dict_data_questions)
            for answer in data_answers:
                obj_raw = {'completed': answer['completed'], 'token': answer['token']}
                if answer['answers']:
                    for k, v in answer['answers'].items():
                        if k in dict_data_questions.keys():
                            obj_raw[dict_data_questions[k]] = v
                else:
                    for k in dict_data_questions.keys():
                        obj_raw[dict_data_questions[k]] = ''
                obj_raw['submitted_at'] = answer['metadata']['date_submit']
                list_data_answers.append(obj_raw)
        new_data = []
        for item in list_data_answers:
            unique_value = item['token']
            q = StoredData.objects.filter(connection=connection_object.connection, plug=plug, object_id=unique_value)
            if not q.exists():
                new_item = [StoredData(name=key, value=value or '', object_id=unique_value, plug=plug,
                                       connection=connection_object.connection) for key, value in item.items()]
                new_data.append(new_item)
        # Result list
        result_list = []
        for item in new_data:
            for stored_data in item:
                try:
                    stored_data.save()
                except Exception as e:
                    is_stored = False
                    break
                is_stored = True
            obj_raw = None
            result_list.append({'identifier': {'name': 'token', 'value': stored_data.object_id}, 'is_stored': is_stored,
                                'raw': list_data_answers[0]})
        obj_last_source_record = False
        return {'downloaded_data': result_list, 'last_source_record': obj_last_source_record}

    def get_action_specification_options(self, action_specification_id):
        action_specification = ActionSpecification.objects.get(pk=action_specification_id)
        if action_specification.name.lower() == 'form':
            forms = self._client.get_forms()
            return tuple({'id': f['id'], 'name': f['name']} for f in forms)
        else:
            raise ControllerError("That specification doesn't belong to an action in this connector.")

    def has_webhook(self):
        return True
