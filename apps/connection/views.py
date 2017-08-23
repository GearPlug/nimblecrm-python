import tweepy
import httplib2
from instagram.client import InstagramAPI
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, View, TemplateView
from django.core.urlresolvers import reverse
from django.http import JsonResponse
from django.shortcuts import redirect
from apps.connection.apps import APP_NAME as app_name
from apps.gp.enum import ConnectorEnum, GoogleAPIEnum
from apps.gp.models import Connection, Connector, MercadoLibreConnection
from oauth2client import client
from requests_oauthlib import OAuth2Session
from slacker import Slacker
import json
import urllib
import requests
from evernote.api.client import EvernoteClient
from meli_client import meli


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
            if connector == ConnectorEnum.FacebookLeads:
                controller_class = ConnectorEnum.get_controller(connector)
                controller = controller_class()
                token = self.request.POST.get('token', '')
                form.instance.token = controller.extend_token(token)
            elif connector in [ConnectorEnum.GoogleSpreadSheets, ConnectorEnum.GoogleContacts,
                               ConnectorEnum.GoogleForms, ConnectorEnum.GoogleCalendar, ConnectorEnum.YouTube]:
                form.instance.credentials_json = self.request.session['google_credentials']
            self.object = form.save()
            self.request.session['auto_select_connection_id'] = c.id
        if self.request.is_ajax():
            return JsonResponse({'data': self.object.id is not None})
        return super(CreateConnectionView, self).form_valid(form, *args, **kwargs)

    def get(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
            self.model, self.fields = ConnectorEnum.get_connector_data(connector)

            if connector.connection_type == 'special':
                name = '{0}/create'.format(connector.name.lower())
            elif connector.connection_type == 'authorization':
                name = 'create_with_auth'
            else:
                name = 'create'
            self.template_name = '%s/%s.html' % (app_name, name)
        return super(CreateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
            self.model, self.fields = ConnectorEnum.get_connector_data(connector)
            if connector.connection_type == 'special':
                name = '{0}/create'.format(connector.name.lower())
            elif connector.connection_type == 'authorization':
                name = 'create_with_auth'
            else:
                name = 'create'
            self.template_name = '%s/%s.html' % (app_name, name)
        return super(CreateConnectionView, self).post(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
        context = super(CreateConnectionView, self).get_context_data(**kwargs)
        context['connection'] = connector.name
        context['connector_name'] = connector.name
        context['connector_id'] = connector.value
        if connector in [ConnectorEnum.GoogleSpreadSheets, ConnectorEnum.GoogleForms, ConnectorEnum.GoogleContacts,
                         ConnectorEnum.GoogleCalendar, ConnectorEnum.YouTube]:
            api = GoogleAPIEnum.get_api(connector.name)
            flow = get_flow(settings.GOOGLE_AUTH_CALLBACK_URL, scope=api.scope)
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = api.name.lower()
        elif connector == ConnectorEnum.Slack:
            context['authorization_url'] = settings.SLACK_PERMISSIONS_URL
        elif connector == ConnectorEnum.Twitter:
            flow = tweepy.OAuthHandler(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET)
            context['authorization_url'] = flow.get_authorization_url()
            self.request.session['twitter_request_token'] = flow.request_token
        elif connector == ConnectorEnum.SurveyMonkey:
            context['authorization_url'] = get_survey_monkey_url()
        elif connector == ConnectorEnum.Shopify:
            context['authorization_url'] = get_shopify_url()
        elif connector == ConnectorEnum.Instagram:
            flow = InstagramAPI(client_id=settings.INSTAGRAM_CLIENT_ID, client_secret=settings.INSTAGRAM_CLIENT_SECRET,
                                redirect_uri=settings.INSTAGRAM_AUTH_URL)
            context['authorizaton_url'] = flow.get_authorize_login_url(scope=settings.INSTAGRAM_SCOPE)
        elif connector == ConnectorEnum.Salesforce:
            flow = get_salesforce_auth()
            context['authorization_url'] = flow
        elif connector == ConnectorEnum.HubSpot:
            context['authorizaton_url'] = get_hubspot_url()
        elif connector == ConnectorEnum.Evernote:
            client = EvernoteClient(consumer_key=settings.EVERNOTE_CONSUMER_KEY,
                                    consumer_secret=settings.EVERNOTE_CONSUMER_SECRET, sandbox=True)
            request_token = client.get_request_token(
                settings.EVERNOTE_REDIRECT_URL)
            self.request.session['oauth_secret_evernote'] = request_token['oauth_token_secret']
            context['authorization_url'] = client.get_authorize_url(
                request_token)
        elif connector == ConnectorEnum.Asana:
            oauth = OAuth2Session(client_id=settings.ASANA_CLIENT_ID,
                                  redirect_uri=settings.ASANA_REDIRECT_URL)
            authorization_url, state = oauth.authorization_url(
                'https://app.asana.com/-/oauth_authorize?response_type=code&client_id={0}&redirect_uri={1}&state=1234'
                    .format(settings.ASANA_CLIENT_ID, settings.ASANA_REDIRECT_URL))
            context['authorization_url'] = authorization_url
        elif connector == ConnectorEnum.MercadoLibre:
            m = meli.Meli(client_id=settings.MERCADOLIBRE_CLIENT_ID, client_secret=settings.MERCADOLIBRE_CLIENT_SECRET)
            context['authorization_url'] = m.auth_url(redirect_URI=settings.MERCADOLIBRE_REDIRECT_URL)
            context['sites'] = MercadoLibreConnection.SITES
        elif connector == ConnectorEnum.WunderList:
            oauth = OAuth2Session(client_id=settings.WUNDERLIST_CLIENT_ID,
                                  redirect_uri=settings.WUNDERLIST_REDIRECT_URL)
            url, state = oauth.authorization_url('https://www.wunderlist.com/oauth/authorize?state=RANDOM')
            context['authorization_url'] = url
        return context


class CreateConnectionSuccessView(LoginRequiredMixin, TemplateView):
    """
    template para cerrar la vnetana al terminar el auth??
    """
    template_name = 'connection/create_connection_success.html'
    login_url = '/account/login/'


class CreateTokenAuthorizedConnectionView(TemplateView):
    template_name = 'connection/auth_success.html'

    def get(self, request, **kwargs):
        if 'connection_data' in self.request.session:
            data = self.request.session['connection_data']
            connector = ConnectorEnum.get_connector(name=self.request.session['connector_name'])
            connector_model = ConnectorEnum.get_model(connector)
            c = Connection.objects.create(user=request.user, connector_id=connector.value)
            n = int(connector_model.objects.filter(connection__user=request.user).count()) + 1
            data['connection_id'] = c.id
            data['name'] = "{0} Connection # {1}".format(connector.name, n)
            try:
                obj = connector_model.objects.create(**data)
                return redirect(reverse('connection:create_success'))
            except Exception:
                # TODO: Connection Eror
                return redirect(reverse('connection:create_success'))


class AuthSuccess(TemplateView):
    template_name = 'connection/auth_success.html'


class TestConnectionView(LoginRequiredMixin, View):
    """
        Test generic connections without saving any 
        actual connection to the database.
    """

    def post(self, request, **kwargs):
        print(request.POST)
        connector = ConnectorEnum.get_connector(kwargs['connector_id'])
        if 'connection_id' in request.POST:
            connection_object = Connection.objects.get(
                pk=request.POST['connection_id']).related_connection
            controller_class = ConnectorEnum.get_controller(connector)
            controller = controller_class(connection_object)
        else:
            connection_model = ConnectorEnum.get_model(connector)
            connection_params = {key: str(val)
                                 for key, val in request.POST.items()}
            del (connection_params['csrfmiddlewaretoken'])
            connection_object = connection_model(**connection_params)
            controller_class = ConnectorEnum.get_controller(connector)
            controller = controller_class(connection_object)
        return JsonResponse({'data': controller.test_connection(), 'connection_test': controller.test_connection()})


# Auth Views

class FacebookAuthView(View):
    def get(self, request, *args, **kwargs):
        print(request.GET)


class MercadoLibreAuthView(View):
    def get(self, request, *args, **kwargs):
        m = meli.Meli(client_id=settings.MERCADOLIBRE_CLIENT_ID, client_secret=settings.MERCADOLIBRE_CLIENT_SECRET)
        token = m.mlo.authorize(code=request.GET.get('code'), redirect_URI=settings.MERCADOLIBRE_REDIRECT_URL)
        request.session['connection_data'] = {'token': token, 'site': 'TODO: site_id?'}
        request.session['connector_name'] = ConnectorEnum.MercadoLibre.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class GoogleAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', None)
        if 'google_connection_type' in request.session and code is not None:
            api = GoogleAPIEnum.get_api(request.session['google_connection_type'])
            credentials = get_flow(settings.GOOGLE_AUTH_CALLBACK_URL, scope=api.scope).step2_exchange(code)
            request.session['connection_data'] = {'credentials_json': credentials.to_json(), }
            request.session['connector_name'] = api.name
            return redirect(reverse('connection:create_token_authorized_connection'))


class InstagramAuthView(View):
    def get(self, request, *args, **kwargs):
        flow = InstagramAPI(client_id=settings.INSTAGRAM_CLIENT_ID, client_secret=settings.INSTAGRAM_CLIENT_SECRET,
                            redirect_uri=settings.INSTAGRAM_AUTH_URL)
        access_token = flow.exchange_code_for_access_token(request.GET['code'])
        request.session['connector_data'] = {'token': access_token[0]}
        request.session['connector_name'] = ConnectorEnum.Instagram.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class SalesforceAuthView(View):
    def get(self, request, *args, **kwargs):
        headers = {'content-type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'authorization_code', 'redirect_uri': settings.SALESFORCE_REDIRECT_URI,
                'code': request.GET['code'], 'client_id': settings.SALESFORCE_CLIENT_ID,
                'client_secret': settings.SALESFORCE_CLIENT_SECRET}
        response = requests.post(settings.SALESFORCE_ACCESS_TOKEN_URL, data=data, headers=headers).json()
        request.session['connection_data'] = {'token': response['access_token'], }
        request.session['connector_name'] = ConnectorEnum.Salesforce.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class SlackAuthView(View):
    def get(self, request):
        code = request.GET.get('code', None)
        if code:
            slack = Slacker("")
            auth_client = slack.oauth.access(client_id=settings.SLACK_CLIENT_ID,
                                             client_secret=settings.SLACK_CLIENT_SECRET, code=code)
            data = json.loads(auth_client.raw)
            token = data['access_token'] if 'access_token' in data else None
            request.session['connection_data'] = {'token': token, }
            request.session['connector_name'] = ConnectorEnum.Slack.name
            return redirect('connection:create_token_authorized_connection')
        # TODO: MENSAJE ERROR
        return redirect('connection:create_token_authorized_connection')


class EvernoteAuthView(View):
    def get(self, request, *args, **kwargs):
        oauth_token = request.GET.get('oauth_token', '')
        val = request.GET.get('oauth_verifier', '')
        oauth_secret = self.request.session['oauth_secret_evernote']
        client = EvernoteClient(consumer_key=settings.EVERNOTE_CONSUMER_KEY,
                                consumer_secret=settings.EVERNOTE_CONSUMER_SECRET, sandbox=True)
        auth_token = client.get_access_token(oauth_token, oauth_secret, val)
        self.request.session['connection_data'] = {'token': auth_token, }
        self.request.session['connector_name'] = ConnectorEnum.Evernote.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class AsanaAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        oauth = OAuth2Session(client_id=settings.ASANA_CLIENT_ID, redirect_uri=settings.ASANA_REDIRECT_URL)
        token = oauth.fetch_token('https://app.asana.com/-/oauth_token', code=code,
                                  authorization_response=settings.ASANA_REDIRECT_URL,
                                  client_id=settings.ASANA_CLIENT_ID, client_secret=settings.ASANA_CLIENT_SECRET, )
        self.request.session['connection_data'] = {'token': token['access_token'],
                                                   'refresh_token': token['refresh_token'],
                                                   'token_expiration_timestamp': token['expires_at']}
        self.request.session['connector_name'] = ConnectorEnum.Asana.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class WunderListAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        oauth = OAuth2Session(client_id=settings.WUNDERLIST_CLIENT_ID, redirect_uri=settings.WUNDERLIST_REDIRECT_URL)
        token = oauth.fetch_token('https://www.wunderlist.com/oauth/access_token',
                                  client_secret=settings.WUNDERLIST_CLIENT_SECRET, code=code, )
        self.request.session['connection_data'] = {'token': token['access_token'], }
        self.request.session['connector_name'] = ConnectorEnum.WunderList.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class TwitterAuthView(View):
    def get(self, request, *args, **kwargs):
        flow = tweepy.OAuthHandler(settings.TWITTER_CLIENT_ID, settings.TWITTER_CLIENT_SECRET)
        flow.request_token = request.session.pop('twitter_request_token')
        flow.get_access_token(request.GET['oauth_verifier'])
        self.request.session['connection_data'] = {'token': flow.access_token, 'token_secret': flow.access_token_secret}
        self.request.session['connector_name'] = ConnectorEnum.Twitter.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class SurveyMonkeyAuthView(View):
    def get(self, request, *args, **kwargs):
        auth_code = request.GET.get('code', None)
        data = {"client_secret": settings.SURVEYMONKEY_CLIENT_SECRET, "code": auth_code,
                "redirect_uri": settings.SURVEYMONKEY_REDIRECT_URI, "client_id": settings.SURVEYMONKEY_CLIENT_ID,
                "grant_type": "authorization_code"}
        url = settings.SURVEYMONKEY_API_BASE + settings.SURVEYMONKEY_ACCESS_TOKEN_ENDPOINT
        response = requests.post(url, data=data).json()
        self.request.session['connection_data'] = {'token': response["access_token"], }
        self.request.session['connector_name'] = ConnectorEnum.SurveyMonkey.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class HubspotAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        data = {'grant_type': 'authorization_code', 'client_id': settings.HUBSPOT_CLIENT_ID, 'code': code,
                'client_secret': settings.HUBSPOT_CLIENT_SECRET, 'redirect_uri': settings.HUBSPOT_REDIRECT_URI, }
        headers = {'Content-Type': 'application/x-www-form-urlencoded', 'charset': 'utf-8'}
        response = requests.post("https://api.hubapi.com/oauth/v1/token", headers=headers, data=data).json()
        self.request.session['connection_data'] = {'token': response['access_token'],
                                                   'refresh_token': response['refresh_token']}
        return redirect(reverse('connection:create_token_authorized_connection'))


class ShopifyAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', None)
        shop_url = request.GET.get('shop', None)
        url = "https://{0}/admin/oauth/access_token".format(shop_url)
        params = {'client_id': settings.SHOPIFY_API_KEY, 'code': code, 'client_secret': settings.SHOPIFY_API_KEY_SECRET}
        try:
            response = requests.post(url, params).json()
            self.request.session['connection_data'] = {'token': response['access_token']}
            self.request.session['connector_name'] = ConnectorEnum.Shopify.name
            return redirect(reverse('connection:create_token_authorized_connection'))
        except Exception as e:
            raise
        # TODO: error
        return redirect(reverse('connection:shopify_success_create_connection'))


# NPI
class AjaxMercadoLibrePostSiteView(View):
    def post(self, request, *args, **kwargs):
        request.session['mercadolibre_site'] = request.POST.get('site_id', None)
        return JsonResponse({'success': True})


def get_salesforce_auth():
    return 'https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id={}&redirect_uri={}'.format(
        settings.SALESFORCE_CLIENT_ID, settings.SALESFORCE_REDIRECT_URI)


def get_survey_monkey_url():
    url_params = urllib.parse.urlencode({"redirect_uri": settings.SURVEYMONKEY_REDIRECT_URI,
                                         "client_id": settings.SURVEYMONKEY_CLIENT_ID, "response_type": "code"})
    return '{0}{1}?{2}'.format(settings.SURVEYMONKEY_API_BASE, settings.SURVEYMONKEY_AUTH_CODE_ENDPOINT, url_params)


def get_shopify_url():
    return "https://{0}.myshopify.com/admin/oauth/authorize?client_id={1}&scope={2}&redirect_uri={3}".format(
        'xxxx', settings.SHOPIFY_API_KEY, settings.SHOPIFY_SCOPE, settings.SHOPIFY_REDIRECT_URI)


def get_hubspot_url():
    return "https://app.hubspot.com/oauth/1234/authorize?client_id={0}&scope=contacts&redirect_uri={1}".format(
        settings.HUBSPOT_CLIENT_ID, settings.HUBSPOT_REDIRECT_URI)


def get_evernote_url():
    client = EvernoteClient(consumer_key=settings.EVERNOTE_CONSUMER_KEY,
                            consumer_secret=settings.EVERNOTE_CONSUMER_SECRET, sandbox=True)
    request_token = client.get_request_token(settings.EVERNOTE_REDIRECT_URL)
    return client.get_authorize_url(request_token)


def get_flow(redirect_to, scope='https://www.googleapis.com/auth/drive'):
    return client.OAuth2WebServerFlow(client_id=settings.GOOGLE_CLIENT_ID, client_secret=settings.GOOGLE_CLIENT_SECRET,
                                      scope=scope, redirect_uri=redirect_to)


def get_authorization(request):
    credentials = client.OAuth2Credentials.from_json(request.session['google_credentials'])
    return credentials.authorize(httplib2.Http())
