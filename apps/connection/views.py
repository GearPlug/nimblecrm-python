import tweepy
from instagram.client import InstagramAPI
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, View
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, HttpResponse
from apps.connection.apps import APP_NAME as app_name
from apps.connection.myviews.FacebookViews import *
from apps.connection.myviews.MySQLViews import *
from apps.connection.myviews.SugarCRMViews import *
from apps.connection.myviews.PostgreSQLViews import *
from apps.connection.myviews.MSSQLViews import *
from apps.connection.myviews.BitbucketViews import *
from apps.connection.myviews.JiraViews import *
from apps.connection.myviews.ZohoCRMViews import *
from apps.connection.myviews.GetResponseViews import *
from apps.connection.myviews.SurveyMonkeyViews import *
from apps.connection.myviews.SMSViews import *
from apps.connection.myviews.SalesforceViews import *
from apps.connection.myviews.SMTPViews import *
from apps.connection.myviews.MandrillViews import *
from apps.connection.myviews.MercadoLibreViews import *
from apps.connection.myviews.MailChimpViews import *
from apps.connection.myviews.GoogleSpreadSheetViews import *
from apps.gp.enum import ConnectorEnum, GoogleAPI
from apps.gp.models import Connection, Connector, GoogleSpreadSheetsConnection, SlackConnection, GoogleFormsConnection, \
    GoogleContactsConnection, TwitterConnection, SurveyMonkeyConnection, InstagramConnection, GoogleCalendarConnection, \
    YouTubeConnection, SMSConnection, ShopifyConnection, HubSpotConnection, MySQLConnection, EvernoteConnection, \
    SalesforceConnection, MercadoLibreConnection

from oauth2client import client
from requests_oauthlib import OAuth2Session
from apiconnector.settings import SLACK_PERMISSIONS_URL, SLACK_CLIENT_SECRET, SLACK_CLIENT_ID
from slacker import Slacker
import json
import urllib
import requests
from evernote.api.client import EvernoteClient
import evernote.edam.type.ttypes as Types
from evernote.edam.notestore.ttypes import NoteFilter, NotesMetadataResultSpec
from meli_client import meli

GOOGLE_DRIVE_SCOPE = ''
GOOGLE_AUTH_URL = 'http://localhost:8000/connection/google_auth/'
GOOGLE_AUTH_REDIRECT_URL = 'connection:google_auth_success_create_connection'

GOOGLE_FORMS_SCOPE = ''
GOOGLE_FORMS_AUTH_URL = 'http://localhost:8000/connection/google_forms_auth/'
GOOGLE_FORMS_AUTH_REDIRECT_URL = 'connection:google_forms_auth_success_create_connection'

GOOGLE_CONTACTS_SCOPE = 'https://www.google.com/m8/feeds/'
GOOGLE_CONTACTS_AUTH_URL = GOOGLE_AUTH_URL
GOOGLE_CONTACTS_AUTH_REDIRECT_URL = GOOGLE_AUTH_REDIRECT_URL

INSTAGRAM_SCOPE = ['basic']
INSTAGRAM_AUTH_URL = 'http://m.gearplug.com/connection/instagram_auth/'
INSTAGRAM_AUTH_REDIRECT_URL = 'connection:instagram_auth_success_create_connection'

GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar'
GOOGLE_CALENDAR_AUTH_URL = 'http://localhost:8000/connection/google_calendar_auth/'
GOOGLE_CALENDAR_AUTH_REDIRECT_URL = 'connection:google_calendar_auth_success_create_connection'

GOOGLE_YOUTUBE_SCOPE = 'https://www.googleapis.com/auth/youtube.readonly https://www.googleapis.com/auth/youtube.upload'
GOOGLE_YOUTUBE_AUTH_URL = 'https://m.grplug.com/connection/google_youtube_auth/'
GOOGLE_YOUTUBE_AUTH_REDIRECT_URL = 'connection:google_youtube_auth_success_create_connection'


class ListConnectorView(LoginRequiredMixin, ListView):
    """
    Lists all connectors that can be used as the type requested.

    - Called after creating a gear.
    - Called after testing the source plug.

    """
    model = Connector
    template_name = 'wizard/connector_list.html'
    login_url = '/account/login/'

    def get_queryset(self):
        if self.kwargs['type'].lower() == 'source':
            kw = {'is_source': True}
        elif self.kwargs['type'].lower() == 'target':
            kw = {'is_target': True}
        else:
            raise (Exception("Not an available type. must be either Source or Target."))
        return self.model.objects.filter(**kw)

    def get_context_data(self, **kwargs):
        context = super(ListConnectorView, self).get_context_data(**kwargs)
        context['type'] = self.kwargs['type']
        return context


class ListConnectionView(LoginRequiredMixin, ListView):
    """
    Lists all connections related to the authenticated user for a specific connector.

    - Called after the user selects a connector to use/create a connection.

    """
    model = Connection
    template_name = 'wizard/connection_list.html'
    login_url = '/account/login/'

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user,
                                         connector_id=self.kwargs['connector_id']).prefetch_related()

    def get_context_data(self, **kwargs):
        context = super(ListConnectionView, self).get_context_data(**kwargs)
        context['connector_id'] = self.kwargs['connector_id']
        return context

    def post(self, request, *args, **kwargs):
        self.object_list = []
        connection_id = request.POST.get('connection', None)
        connector_type = kwargs['type']
        request.session['%s_connection_id' % connector_type] = connection_id
        return redirect(reverse('wizard:plug_create', kwargs={'plug_type': connector_type}))


class CreateConnectionView(LoginRequiredMixin, CreateView):
    """
    Clase para crear conexion.
    - llamado desde lista de conexiones en caso tal que el usuario desee
    crear una nueva conexion.
    """
    model = Connection
    login_url = '/account/login/'
    fields = []
    template_name = '%s/create.html' % app_name
    success_url = reverse_lazy('%s:create_success' % app_name)

    def form_valid(self, form, *args, **kwargs):
        connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
        if self.kwargs['connector_id'] is not None:
            c = Connection.objects.create(user=self.request.user, connector_id=self.kwargs['connector_id'])
            form.instance.connection = c
            if connector == ConnectorEnum.Facebook:  # Extender token de facebook antes de guardar.
                facebook_controller = FacebookLeadsController()
                form.instance.token = facebook_controller.extend_token(self.request.POST.get('token', ''))
            elif connector in [ConnectorEnum.GoogleSpreadSheets, ConnectorEnum.GoogleContacts,
                               ConnectorEnum.GoogleForms, ConnectorEnum.GoogleCalendar, ConnectorEnum.YouTube]:
                # Guardar credenciales de google en el formulario (deben venir en la sessión).
                form.instance.credentials_json = self.request.session['google_credentials']
            self.object = form.save()
            self.request.session['auto_select_connection_id'] = c.id
        if self.request.is_ajax():  # Si es ajax devolver True si se guarda en base de datos el objeto.
            return JsonResponse({'data': self.object.id is not None})
        return super(CreateConnectionView, self).form_valid(form, *args, **kwargs)

    def get(self, *args, **kwargs):
        # El model y los fields varían dependiendo de la conexion.
        if self.kwargs['connector_id'] is not None:
            connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
            self.model, self.fields = ConnectorEnum.get_connector_data(connector)
            # Creación con url de authorization como OAuth (Trabajan con token en su mayoria.)
            if connector.name.lower() in ['googlesheets', 'slack', 'surveymonkey', 'evernote', 'asana']:
                name = 'create_with_auth'
            elif connector.name.lower() in ['facebook', 'hubspot', 'mercadolibre']:  # Especial
                name = '{0}/create'.format(connector.name.lower())
            else:  # Sin autorization. Creación por formulario.
                name = 'create'
            self.template_name = '%s/%s.html' % (app_name, name)
        return super(CreateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        # El model y los fields varían dependiendo de la conexion.
        if self.kwargs['connector_id'] is not None:
            connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
            self.model, self.fields = ConnectorEnum.get_connector_data(connector)
            # Creación con url de authorization como OAuth (Trabajan con token en su mayoria.)
            if connector.name.lower() in ['googlesheets', 'slack', 'surveymonkey', 'evernote', 'asana']:
                name = 'create_with_auth'
            elif connector.name.lower() in ['facebook', 'hubspot', 'mercadolibre']:  # Especial
                name = '{0}/create'.format(connector.name.lower())
            else:  # Sin autorization. Creación por formulario.
                name = 'create'
            self.template_name = '%s/%s.html' % (app_name, name)
        return super(CreateConnectionView, self).post(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
        context = super(CreateConnectionView, self).get_context_data(**kwargs)
        context['connection'] = connector.name
        context['connector_name'] = connector.name
        context['connector_id'] = connector.value
        if connector == ConnectorEnum.GoogleSpreadSheets:
            flow = get_flow(GOOGLE_AUTH_URL)
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'drive'
        elif connector == ConnectorEnum.GoogleForms:
            flow = get_flow(GOOGLE_FORMS_AUTH_URL)
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'forms'
        elif connector == ConnectorEnum.GoogleContacts:
            flow = get_flow_google_contacts()
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'contacts'
        elif connector == ConnectorEnum.GoogleCalendar:
            flow = get_flow(GOOGLE_CALENDAR_AUTH_URL, GOOGLE_CALENDAR_SCOPE)
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'calendar'
        elif connector == ConnectorEnum.YouTube:
            flow = get_flow(GOOGLE_YOUTUBE_AUTH_URL, GOOGLE_YOUTUBE_SCOPE)
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'youtube'
        elif connector == ConnectorEnum.Slack:
            context['authorization_url'] = SLACK_PERMISSIONS_URL
        elif connector == ConnectorEnum.Twitter:
            flow = get_twitter_auth()
            context['authorization_url'] = flow.get_authorization_url()
            self.request.session['twitter_request_token'] = flow.request_token
        elif connector == ConnectorEnum.SurveyMonkey:
            context['authorization_url'] = get_survey_monkey_url()
        elif connector == ConnectorEnum.Shopify:
            context['authorization_url'] = get_shopify_url()
        elif connector == ConnectorEnum.Instagram:
            flow = get_instagram_auth()
            context['authorizaton_url'] = flow.get_authorize_login_url(scope=INSTAGRAM_SCOPE)
        elif connector == ConnectorEnum.Salesforce:
            flow = get_salesforce_auth()
            context['authorizaton_url'] = flow
        elif connector == ConnectorEnum.HubSpot:
            context['authorizaton_url'] = get_hubspot_url()
        elif connector == ConnectorEnum.Evernote:
            client = EvernoteClient(consumer_key=settings.EVERNOTE_CONSUMER_KEY,
                                    consumer_secret=settings.EVERNOTE_CONSUMER_SECRET, sandbox=True)
            request_token = client.get_request_token(settings.EVERNOTE_REDIRECT_URL)
            self.request.session['oauth_secret_evernote'] = request_token['oauth_token_secret']
            context['authorization_url'] = client.get_authorize_url(request_token)
        elif connector == ConnectorEnum.Asana:
            oauth = OAuth2Session(client_id=settings.ASANA_CLIENT_ID,
                                  redirect_uri=settings.ASANA_REDIRECT_URL)
            authorization_url, state = oauth.authorization_url(
                'https://app.asana.com/-/oauth_authorize?response_type=code&client_id={0}&redirect_uri={1}&state=1234'
                    .format(settings.ASANA_CLIENT_ID, settings.ASANA_REDIRECT_URL))
            context['authorization_url'] = authorization_url
        elif connector == ConnectorEnum.MercadoLibre:
            flow = get_mercadolibre_auth()
            context['authorization_url'] = flow
            context['sites'] = MercadoLibreConnection.SITES
        return context


class CreateConnectionSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'connection/create_connection_success.html'
    login_url = '/account/login/'


class TestConnectionView(LoginRequiredMixin, View):
    """
        Test generic connections without saving any actual connection to the database.
    """

    def post(self, request, **kwargs):
        connector = ConnectorEnum.get_connector(kwargs['connector_id'])
        if 'connection_id' in request.POST:
            connection_object = Connection.objects.get(pk=request.POST['connection_id']).related_connection
            controller_class = ConnectorEnum.get_controller(connector)
            controller = controller_class(connection_object)
        else:
            connection_model = ConnectorEnum.get_model(connector)
            connection_params = {key: str(val) for key, val in request.POST.items()}
            del (connection_params['csrfmiddlewaretoken'])
            connection_object = connection_model(**connection_params)
            controller_class = ConnectorEnum.get_controller(connector)
            controller = controller_class(connection_object)
        return JsonResponse({'data': controller.test_connection(), 'connection_test': controller.test_connection()})


class MercadoLibreAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET['code']
        token = get_mercadolibre_auth(code)
        request.session['mercadolibre_code'] = token
        return redirect(reverse('connection:mercadolibre_auth_success_create_connection'))


class AjaxMercadoLibrePostSiteView(View):
    def post(self, request, *args, **kwargs):
        request.session['mercadolibre_site'] = request.POST.get('site_id', None)
        return JsonResponse({'success': True})


class MercadoLibreAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/mercadolibre/success.html'

    def get(self, request, *args, **kwargs):
        try:
            if 'mercadolibre_code' in request.session and 'mercadolibre_site' in request.session:
                access_token = request.session.pop('mercadolibre_code')
                site_id = request.session.pop('mercadolibre_site')
                c = Connection.objects.create(user=request.user, connector_id=ConnectorEnum.MercadoLibre.value)
                n = int(MercadoLibreConnection.objects.filter(connection__user=request.user).count()) + 1
                mlc = MercadoLibreConnection.objects.create(connection=c, name="MercadoLibre Connection # %s" % n,
                                                            token=access_token, site=site_id)
        except Exception as e:
            print("Error creating the MercadoLibre Connection.")
            raise
        return super(MercadoLibreAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


class GoogleAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET['code']
        if kwargs['api'] == GoogleAPI.Forms:
            credentials = get_flow(GOOGLE_FORMS_AUTH_URL).step2_exchange(code)
            request.session['google_credentials'] = credentials.to_json()
            return redirect(reverse(GOOGLE_FORMS_AUTH_REDIRECT_URL))
        elif kwargs['api'] == GoogleAPI.SpreadSheets:
            credentials = get_flow(GOOGLE_AUTH_URL).step2_exchange(code)
            request.session['google_credentials'] = credentials.to_json()
            return redirect(reverse(GOOGLE_AUTH_REDIRECT_URL))
        elif kwargs['api'] == GoogleAPI.Calendar:
            credentials = get_flow(GOOGLE_CALENDAR_AUTH_URL, GOOGLE_CALENDAR_SCOPE).step2_exchange(code)
            request.session['google_credentials'] = credentials.to_json()
            return redirect(reverse(GOOGLE_CALENDAR_AUTH_REDIRECT_URL))
        elif kwargs['api'] == GoogleAPI.YouTube:
            credentials = get_flow(GOOGLE_YOUTUBE_AUTH_URL, GOOGLE_YOUTUBE_SCOPE).step2_exchange(code)
            request.session['google_credentials'] = credentials.to_json()
            return redirect(reverse(GOOGLE_YOUTUBE_AUTH_REDIRECT_URL))


class GoogleAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/googlespreadsheets/success.html'

    def get(self, request, *args, **kwargs):
        print('auth success')
        try:
            if 'google_credentials' in request.session:
                credentials = request.session.pop('google_credentials')
                if kwargs['api'] == GoogleAPI.Forms:
                    c = Connection.objects.create(
                        user=request.user, connector_id=ConnectorEnum.GoogleForms.value)
                    n = int(GoogleFormsConnection.objects.filter(connection__user=request.user).count()) + 1
                    gssc = GoogleFormsConnection.objects.create(
                        connection=c, name="GoogleForms Connection # %s" % n, credentials_json=credentials)
                elif kwargs['api'] == GoogleAPI.SpreadSheets:
                    c = Connection.objects.create(
                        user=request.user, connector_id=ConnectorEnum.GoogleSpreadSheets.value)
                    n = int(GoogleSpreadSheetsConnection.objects.filter(connection__user=request.user).count()) + 1
                    gssc = GoogleSpreadSheetsConnection.objects.create(
                        connection=c, name="GoogleSheets Connection # %s" % n, credentials_json=credentials)
                elif kwargs['api'] == GoogleAPI.Calendar:
                    c = Connection.objects.create(
                        user=request.user, connector_id=ConnectorEnum.GoogleCalendar.value)
                    n = int(GoogleCalendarConnection.objects.filter(connection__user=request.user).count()) + 1
                    gssc = GoogleCalendarConnection.objects.create(
                        connection=c, name="GoogleCalendar Connection # %s" % n, credentials_json=credentials)
                elif kwargs['api'] == GoogleAPI.YouTube:
                    c = Connection.objects.create(
                        user=request.user, connector_id=ConnectorEnum.YouTube.value)
                    n = int(YouTubeConnection.objects.filter(connection__user=request.user).count()) + 1
                    gssc = YouTubeConnection.objects.create(
                        connection=c, name="YouTube Connection # %s" % n, credentials_json=credentials)
        except Exception as e:
            raise
        return super(GoogleAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


class TwitterAuthView(View):
    def get(self, request, *args, **kwargs):
        flow = get_twitter_auth()
        flow.request_token = request.session.pop('twitter_request_token')
        flow.get_access_token(request.GET['oauth_verifier'])
        request.session['twitter_access_token'] = flow.access_token
        request.session['twitter_access_token_secret'] = flow.access_token_secret
        return redirect(reverse('connection:twitter_auth_success_create_connection'))


class TwitterAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/googlespreadsheets/success.html'

    def get(self, request, *args, **kwargs):
        try:
            if 'twitter_access_token' in request.session and 'twitter_access_token_secret' in request.session:
                access_token = request.session.pop('twitter_access_token')
                access_token_secret = request.session.pop('twitter_access_token_secret')
                c = Connection.objects.create(
                    user=request.user, connector_id=ConnectorEnum.Twitter.value)
                n = int(TwitterConnection.objects.filter(connection__user=request.user).count()) + 1
                tc = TwitterConnection.objects.create(
                    connection=c, name="Twitter Connection # %s" % n, token=access_token,
                    token_secret=access_token_secret)
        except Exception as e:
            print("Error creating the Twitter Connection.")
        return super(TwitterAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


def get_twitter_auth():
    consumer_key = settings.TWITTER_CLIENT_ID
    consumer_secret = settings.TWITTER_CLIENT_SECRET
    return tweepy.OAuthHandler(consumer_key, consumer_secret)


class InstagramAuthView(View):
    def get(self, request, *args, **kwargs):
        flow = get_instagram_auth()
        access_token = flow.exchange_code_for_access_token(request.GET['code'])
        print(access_token[0])
        request.session['instagram_access_token'] = access_token[0]
        return redirect(reverse('connection:instagram_auth_success_create_connection'))


class InstagramAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/instagram/success.html'

    def get(self, request, *args, **kwargs):
        try:
            if 'instagram_access_token' in request.session:
                access_token = request.session.pop('instagram_access_token')
                print(access_token)
                print(request.user)
                print(ConnectorEnum.Instagram.value)
                c = Connection.objects.create(
                    user=request.user, connector_id=ConnectorEnum.Instagram.value)
                print(c)
                n = int(InstagramConnection.objects.filter(connection__user=request.user).count()) + 1
                print(n)
                tc = InstagramConnection.objects.create(
                    connection=c, name="Instagram Connection # %s" % n, token=access_token)
                print(tc)
        except Exception as e:
            print("Error creating the Instagram Connection.")
        return super(InstagramAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


def get_instagram_auth():
    return InstagramAPI(client_id=settings.INSTAGRAM_CLIENT_ID, client_secret=settings.INSTAGRAM_CLIENT_SECRET,
                        redirect_uri=INSTAGRAM_AUTH_URL)


def get_mercadolibre_auth(code=None):
    meli_obj = meli.Meli(client_id=settings.MERCADOLIBRE_CLIENT_ID, client_secret=settings.MERCADOLIBRE_CLIENT_SECRET)
    if code:
        return meli_obj.authorize(code=code, redirect_URI=settings.MERCADOLIBRE_REDIRECT_URL)
    else:
        return meli_obj.auth_url(redirect_URI=settings.MERCADOLIBRE_REDIRECT_URL)


class SalesforceAuthView(View):
    def get(self, request, *args, **kwargs):
        headers = {
            'content-type': 'application/x-www-form-urlencoded'
        }

        data = {
            'grant_type': 'authorization_code',
            'redirect_uri': settings.SALESFORCE_REDIRECT_URI,
            'code': request.GET['code'],
            'client_id': settings.SALESFORCE_CLIENT_ID,
            'client_secret': settings.SALESFORCE_CLIENT_SECRET
        }

        req = requests.post(settings.SALESFORCE_ACCESS_TOKEN_URL, data=data, headers=headers)
        response = req.json()

        request.session['salesforce_access_token'] = response['access_token']
        return redirect(reverse('connection:salesforce_auth_success_create_connection'))


class SalesforceAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/instagram/success.html'

    def get(self, request, *args, **kwargs):
        try:
            if 'salesforce_access_token' in request.session:
                access_token = request.session.pop('salesforce_access_token')
                c = Connection.objects.create(
                    user=request.user, connector_id=ConnectorEnum.Salesforce.value)
                n = int(SalesforceConnection.objects.filter(connection__user=request.user).count()) + 1
                tc = SalesforceConnection.objects.create(
                    connection=c, name="Salesforce Connection # %s" % n, token=access_token)
        except Exception as e:
            print("Error creating the Salesforce Connection.")
        return super(SalesforceAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


def get_salesforce_auth():
    return 'https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id={}&redirect_uri={}'.format(
        settings.SALESFORCE_CLIENT_ID, settings.SALESFORCE_REDIRECT_URI)


class SlackAuthView(View):
    def get(self, request):
        code = request.GET.get('code', None)
        if code:
            slack = Slacker("")
            auth_client = slack.oauth.access(client_id=SLACK_CLIENT_ID, client_secret=SLACK_CLIENT_SECRET, code=code)
            data = json.loads(auth_client.raw)
            token = data['access_token'] if 'access_token' in data else None
            print(token)
            slack = Slacker(token)
            ping = slack.auth.test()
            try:
                c = Connection.objects.create(user=request.user, connector_id=ConnectorEnum.Slack.value)
                n = int(SlackConnection.objects.filter(connection__user=request.user).count()) + 1
                sc = SlackConnection.objects.create(connection=c, token=token,
                                                    name="Slack Connection # {0}".format(n))
            except Exception as e:
                print(e)
                print("Error con el slack")
        return redirect('connection:auth_sucess')


class SurveyMonkeyAuthView(View):
    def get(self, request, *args, **kwargs):
        # print("Auth SM - CODE")
        auth_code = request.GET.get('code', None)
        data = {
            "client_secret": settings.SURVEYMONKEY_CLIENT_SECRET,
            "code": auth_code,
            "redirect_uri": settings.SURVEYMONKEY_REDIRECT_URI,
            "client_id": settings.SURVEYMONKEY_CLIENT_ID,
            "grant_type": "authorization_code"
        }
        print(settings.SURVEYMONKEY_REDIRECT_URI)
        try:
            access_token_uri = settings.SURVEYMONKEY_API_BASE + settings.SURVEYMONKEY_ACCESS_TOKEN_ENDPOINT
            access_token_response = requests.post(access_token_uri, data=data)
            access_json = access_token_response.json()
            try:
                self.request.session['survey_monkey_auth_token'] = access_json["access_token"]
                return redirect(reverse('connection:survey_monkey_auth_success_create_connection'))
            except Exception as e:
                raise
                print(e)
                print("Error en survey Monkey")

        except Exception as e:
            raise
            print(e)
            print("Error en Survey Monkey")
        return redirect(reverse('connection:survey_monkey_auth_success_create_connection'))


class SurveyMonkeyAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/surveymonkey/success.html'

    def get(self, request, *args, **kwargs):
        # print("Success SM - Connection")
        try:
            if 'survey_monkey_auth_token' in request.session:
                access_token = request.session.pop('survey_monkey_auth_token')
                c = Connection.objects.create(
                    user=request.user, connector_id=ConnectorEnum.SurveyMonkey.value)
                n = int(SurveyMonkeyConnection.objects.filter(connection__user=request.user).count()) + 1
                tc = SurveyMonkeyConnection.objects.create(
                    connection=c, name="Survey Monkey Connection # %s" % n, token=access_token)
        except Exception as e:
            print("Error creating the Survey Monkey Connection.")
        return super(SurveyMonkeyAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


def get_survey_monkey_url():
    url_params = urllib.parse.urlencode({
        "redirect_uri": settings.SURVEYMONKEY_REDIRECT_URI,
        "client_id": settings.SURVEYMONKEY_CLIENT_ID,
        "response_type": "code"
    })
    return settings.SURVEYMONKEY_API_BASE + settings.SURVEYMONKEY_AUTH_CODE_ENDPOINT + "?" + url_params


class ShopifyAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        url = "https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com/admin/oauth/access_token"
        params = {'client_id': settings.SHOPIFY_API_KEY, 'client_secret': settings.SHOPIFY_API_KEY_SECRET, 'code': code}
        try:
            response = requests.post(url, params).__dict__['_content'].decode()
            token = json.loads(response)['access_token']
            print("token")
            print(token)
            try:
                request.session['shopify_token'] = token
                return redirect(reverse('connection:shopify_auth_success_create_connection'))
            except Exception as e:
                raise
                print(e)
                print("Error en Shopify")

        except Exception as e:
            raise
            print(e)
            print("Error en Shopify")
        return redirect(reverse('connection:shopify_success_create_connection'))


class ShopifyAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/shopify/sucess.html'

    def get(self, request, *args, **kwargs):
        try:
            if 'shopify_token' in request.session:
                access_token = request.session.pop('shopify_token')
                c = Connection.objects.create(
                    user=request.user, connector_id=ConnectorEnum.Shopify.value)
                n = int(ShopifyConnection.objects.filter(connection__user=request.user).count()) + 1
                tc = ShopifyConnection.objects.create(
                    connection=c, name="Shopify Connection # %s" % n, token=access_token)
        except Exception as e:
            print("Error creating Shopify Connection.")
        return super(ShopifyAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


def get_shopify_url():
    scopes = "read_products, write_products, read_orders, read_customers, write_orders, write_customers"
    return "https://" + settings.SHOPIFY_SHOP_URL + ".myshopify.com/admin/oauth/authorize?client_id=" + settings.SHOPIFY_API_KEY + "&scope=" + scopes + "&redirect_uri=" + settings.SHOPIFY_REDIRECT_URI


class HubspotAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        data = {'grant_type': 'authorization_code', 'client_id': settings.HUBSPOT_CLIENT_ID,
                'client_secret': settings.HUBSPOT_CLIENT_SECRET, 'redirect_uri': settings.HUBSPOT_REDIRECT_URI,
                'code': code}
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'charset': 'utf-8'}
        url = "https://api.hubapi.com/oauth/v1/token"
        response = requests.post(url, headers=headers, data=data)
        try:
            response = response.json()
            self.request.session['hubspot_token'] = response['access_token']
            self.request.session['refresh_token'] = response['refresh_token']
            return redirect(reverse('connection:hubspot_auth_success_create_connection'))
        except Exception as e:
            raise
            print(e)
            print("Error en Hubspot")
        return redirect(reverse('connection:hubspot_auth_success_create_connection'))


class HubspotAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/hubspot/sucess.html'

    def get(self, request, *args, **kwargs):
        try:
            if 'hubspot_token' and 'refresh_token' in request.session:
                access_token = request.session.pop('hubspot_token')
                refresh_token = request.session.pop('refresh_token')
                c = Connection.objects.create(user=request.user, connector_id=ConnectorEnum.HubSpot.value)
                n = int(HubSpotConnection.objects.filter(connection__user=request.user).count()) + 1
                tc = HubSpotConnection.objects.create(
                    connection=c, name="Hubspot Connection # %s" % n, token=access_token, refresh_token=refresh_token)
        except Exception as e:
            raise
            print("Error creating Hubspot Connection.")
        return super(HubspotAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


def get_hubspot_url():
    return "https://app.hubspot.com/oauth/1234/authorize?client_id=" + settings.HUBSPOT_CLIENT_ID + "&scope=contacts&redirect_uri=" + settings.HUBSPOT_REDIRECT_URI


class EvernoteAuthView(View):
    def get(self, request, *args, **kwargs):
        oauth_token = request.GET.get('oauth_token', '')
        val = request.GET.get('oauth_verifier', '')
        oauth_secret = self.request.session['oauth_secret_evernote']
        client = EvernoteClient(consumer_key=settings.EVERNOTE_CONSUMER_KEY,
                                consumer_secret=settings.EVERNOTE_CONSUMER_SECRET, sandbox=True)
        auth_token = client.get_access_token(oauth_token, oauth_secret, val)
        self.request.session['auth_token'] = auth_token
        return redirect(reverse('connection:evernote_success_create_connection'))


class EvernoteAuthSuccessCreateConnection(TemplateView):
    template_name = 'connection/evernote/sucess.html'

    def get(self, request, *args, **kwargs):
        try:
            if 'auth_token' in request.session:
                access_token = request.session.pop('auth_token')
                c = Connection.objects.create(
                    user=request.user, connector_id=ConnectorEnum.Evernote.value)
                n = int(EvernoteConnection.objects.filter(connection__user=request.user).count()) + 1
                tc = EvernoteConnection.objects.create(
                    connection=c, name="Evernote Connection # %s" % n, token=access_token)
        except Exception as e:
            print("Error creating Evernote Connection.")
        return super(EvernoteAuthSuccessCreateConnection, self).get(request, *args, **kwargs)


class AsanaAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        oauth = OAuth2Session(client_id=settings.ASANA_CLIENT_ID, redirect_uri=settings.ASANA_REDIRECT_URL)
        token = oauth.fetch_token('https://app.asana.com/-/oauth_token',
                                  authorization_response=settings.ASANA_REDIRECT_URL,
                                  client_id=settings.ASANA_CLIENT_ID,
                                  client_secret=settings.ASANA_CLIENT_SECRET,
                                  code=code,
                                  )
        self.request.session['connection_data'] = {'token': token['access_token'],
                                                   'refresh_token': token['refresh_token'],
                                                   'token_expiration_timestamp': token['expires_at']}
        self.request.session['connector_name'] = ConnectorEnum.Asana.name
        return redirect(reverse('connection:create_authorizated_connection'))


class CreateAuthorizatedConnectionView(View):
    def get(self, request, **kwargs):
        if 'authorization_token' in self.request.session:
            data = self.request.session['connection_data']
            connector_name = self.request.session['connector_name']
        else:
            data = None
        if data is not None:
            print(data)
            connector = ConnectorEnum.get_connector(name=connector_name)
            connector_model = ConnectorEnum.get_model(connector)
            print(connector)
            print(connector_model)

            c = Connection.objects.create(user=request.user, connector_id=connector.value)
            n = int(connector_model.objects.filter(
                connection__user=request.user).count()) + 1
            data['connection_id'] = c.id
            data['name'] = "{0} Connection # {1}".format(connector_name, n)
            print(data)
            obj = connector_model.objects.create(**data)
            print(obj)
            return redirect(reverse('connection:create_success'))


def get_evernote_url():
    client = EvernoteClient(consumer_key=settings.EVERNOTE_CONSUMER_KEY,
                            consumer_secret=settings.EVERNOTE_CONSUMER_SECRET, sandbox=True)
    request_token = client.get_request_token(settings.EVERNOTE_REDIRECT_URL)
    return client.get_authorize_url(request_token)


class AuthSuccess(TemplateView):
    template_name = 'connection/auth_success.html'


def get_flow(redirect_to, scope='https://www.googleapis.com/auth/drive'):
    return client.OAuth2WebServerFlow(
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scope=scope, redirect_uri=redirect_to)


def get_flow_google(client_id, client_secret, scope=None, redirect_uri='http://localhost:8000/connection/google_auth/'):
    return client.OAuth2WebServerFlow(client_id=client_id, client_secret=client_secret, scope=scope,
                                      redirect_uri=redirect_uri)


def get_flow_google_spreadsheets():
    return get_flow_google(client_id='292458000851-9q394cs5t0ekqpfsodm284ve6ifpd7fd.apps.googleusercontent.com',
                           client_secret='eqcecSL7Ecp0hiMy84QFSzsD',
                           scope='https://www.googleapis.com/auth/drive',
                           redirect_uri='http://localhost:8000/connection/google_auth/')


def get_flow_google_contacts():
    return get_flow_google(client_id='292458000851-9q394cs5t0ekqpfsodm284ve6ifpd7fd.apps.googleusercontent.com',
                           client_secret='eqcecSL7Ecp0hiMy84QFSzsD',
                           scope='https://www.google.com/m8/feeds/',
                           redirect_uri='http://localhost:8000/connection/google_auth/')
