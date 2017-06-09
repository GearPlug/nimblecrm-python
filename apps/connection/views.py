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
from apps.connection.myviews.MailChimpViews import *
from apps.connection.myviews.GoogleSpreadSheetViews import *
from apps.gp.enum import ConnectorEnum, GoogleAPI
from apps.gp.models import Connection, Connector, GoogleSpreadSheetsConnection, SlackConnection, GoogleFormsConnection, \
    GoogleContactsConnection, TwitterConnection, SurveyMonkeyConnection, InstagramConnection, GoogleCalendarConnection, \
    YouTubeConnection, SMSConnection
from oauth2client import client
from apiconnector.settings import SLACK_PERMISSIONS_URL, SLACK_CLIENT_SECRET, SLACK_CLIENT_ID
from slacker import Slacker
import json
import urllib
import requests

GOOGLE_DRIVE_SCOPE = 'https://www.googleapis.com/auth/drive'
GOOGLE_AUTH_URL = 'http://localhost:8000/connection/google_auth/'
GOOGLE_AUTH_REDIRECT_URL = 'connection:google_auth_success_create_connection',

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


class CreateConnectionView(CreateView):
    model = Connection
    fields = []
    template_name = '%s/create.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)
    fbc = FacebookController()
    mcc = GoogleSpreadSheetsController()

    def form_valid(self, form, *args, **kwargs):
        print('valid')
        if self.kwargs['connector_id'] is not None:
            c = Connection.objects.create(user=self.request.user, connector_id=self.kwargs['connector_id'])
            form.instance.connection = c
            if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Facebook:
                token = self.request.POST.get('token', '')
                long_user_access_token = self.fbc.extend_token(token)
                form.instance.token = long_user_access_token
            elif ConnectorEnum.get_connector(
                    self.kwargs['connector_id']) == ConnectorEnum.GoogleSpreadSheets or ConnectorEnum.get_connector(
                self.kwargs['connector_id']) == ConnectorEnum.GoogleContacts:
                form.instance.credentials_json = self.request.session['google_credentials']
            elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.GoogleForms:
                form.instance.credentials_json = self.request.session['google_credentials']
            elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.GoogleCalendar:
                form.instance.credentials_json = self.request.session['google_credentials']
            elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.YouTube:
                form.instance.credentials_json = self.request.session['google_credentials']
            return super(CreateConnectionView, self).form_valid(form, *args, **kwargs)

    def get(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
            name = 'ajax_create' if self.request.is_ajax() else 'create'
            self.template_name = '%s/%s/%s.html' % (
                app_name, ConnectorEnum.get_connector(self.kwargs['connector_id']).name.lower(), name)
        return super(CreateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
            name = 'ajax_create' if self.request.is_ajax() else 'create'
            self.template_name = '%s/%s/%s.html' % (
                app_name, ConnectorEnum.get_connector(self.kwargs['connector_id']).name.lower(), name)
        return super(CreateConnectionView, self).post(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateConnectionView, self).get_context_data(**kwargs)
        context['connection'] = ConnectorEnum.get_connector(self.kwargs['connector_id']).name
        if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.GoogleSpreadSheets:
            flow = get_flow(GOOGLE_AUTH_URL)
            context['google_auth_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'drive'
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.GoogleForms:
            flow = get_flow(GOOGLE_FORMS_AUTH_URL)
            context['google_auth_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'forms'
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.GoogleContacts:
            flow = get_flow_google_contacts()
            context['google_auth_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'contacts'
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.GoogleCalendar:
            flow = get_flow(GOOGLE_CALENDAR_AUTH_URL, GOOGLE_CALENDAR_SCOPE)
            context['google_auth_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'calendar'
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.YouTube:
            flow = get_flow(GOOGLE_YOUTUBE_AUTH_URL, GOOGLE_YOUTUBE_SCOPE)
            context['google_auth_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = 'youtube'
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Slack:
            context['slack_auth_url'] = SLACK_PERMISSIONS_URL
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Twitter:
            flow = get_twitter_auth()
            context['twitter_auth_url'] = flow.get_authorization_url()
            self.request.session['twitter_request_token'] = flow.request_token
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.SurveyMonkey:
            # print("Create 1 - SV")
            context['surveymonkey_auth_url'] = get_survey_monkey_url()
        elif ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Instagram:
            flow = get_instagram_auth()
            context['instagram_auth_url'] = flow.get_authorize_login_url(scope=INSTAGRAM_SCOPE)
        return context


class UpdateConnectionView(UpdateView):
    model = Connection
    fields = []
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def get(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
            if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Facebook:
                self.template_name = '%s/%s/update.html' % (app_name, ConnectorEnum.Facebook.name.lower())
        return super(UpdateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
            if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Facebook:
                self.template_name = '%s/%s/update.html' % (app_name, ConnectorEnum.Facebook.name.lower())
        return super(UpdateConnectionView, self).post(*args, **kwargs)


class DeleteConnectionView(DeleteView):
    model = Connection
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


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
            # print("Error creating the GoogleSheets Connection.")
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
            print("access")
            print(access_json)
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
    print("URL SV")
    url_params = urllib.parse.urlencode({
        "redirect_uri": settings.SURVEYMONKEY_REDIRECT_URI,
        "client_id": settings.SURVEYMONKEY_CLIENT_ID,
        "response_type": "code"
    })
    return settings.SURVEYMONKEY_API_BASE + settings.SURVEYMONKEY_AUTH_CODE_ENDPOINT + "?" + url_params


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
