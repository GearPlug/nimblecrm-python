from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.urlresolvers import reverse
from django.db.models import IntegerField, Case, When, Sum, Q
from django.db.models.aggregates import Count
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.template import loader
from django.views.generic import CreateView, ListView, View, TemplateView, UpdateView
from apps.gp.enum import ConnectorEnum, GoogleAPIEnum
from apps.gp.models import Connection, Connector, MercadoLibreConnection, Gear, Category
from urllib.parse import urlencode
from oauth2client import client
from requests_oauthlib import OAuth2Session
from slacker import Slacker
from evernote.api.client import EvernoteClient
from mercadolibre.client import Client as MercadolibreClient
from instagram.client import InstagramAPI
import tweepy
import httplib2
import json
import urllib
import requests
from random import randint


class ListConnectorView(LoginRequiredMixin, ListView):
    """
    Lists all connectors that can be used as the type requested.

    - Called after creating a gear.
    - Called after testing the source plug.

    """
    model = Connector
    template_name = 'connection/connector_list.html'
    login_url = '/accounts/login/'

    def get_queryset(self):
        if self.kwargs['type'].lower() == 'source':
            kw = {'is_source': True}
        elif self.kwargs['type'].lower() == 'target':
            kw = {'is_target': True}
        else:
            raise (Exception(
                "Not an available type. must be either Source or Target."))
        return self.model.objects.filter(**kw).annotate(
            connection_count=Sum(Case(When(connection__user=self.request.user, then=1), default=0,
                                      output_field=IntegerField())))

    def get_context_data(self, **kwargs):
        context = super(ListConnectorView, self).get_context_data(**kwargs)
        context['type'] = self.kwargs['type']
        context['categories'] = Category.objects.all()
        return context


class ListConnectionView(LoginRequiredMixin, ListView):
    """
    Lists all connections related to the authenticated user for a specific connector.

    - Called after the user selects a connector to use/create a connection.

    - Asign the  connection_id to the session.

    """
    model = Connection
    template_name = 'connection/list.html'
    login_url = '/accounts/login/'

    def get(self, request, *args, **kwargs):
        connector = ConnectorEnum.get_connector(kwargs['connector_id'])
        if connector.connection_type is None:
            # TODO: Agregar connection default para el connector. SMS, SMTP y Webhook
            count = Connection.objects.filter(connector_id=connector.value).aggregate(ids=Count('id'))['ids']
            random_index = randint(0, count - 1)
            request.session['%s_connection_id' % kwargs['type']] = Connection.objects.filter(
                connector_id=connector.value)[random_index].id
            return redirect(reverse('plug:create', kwargs={'plug_type': kwargs['type']}))
        request.session['plug_type'] = kwargs['type']
        return super(ListConnectionView, self).get(request, *args, **kwargs)

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
        del request.session['plug_type']
        return redirect(reverse('plug:create', kwargs={'plug_type': connector_type}))


class CreateConnectionView(LoginRequiredMixin, CreateView):
    """
    Clase para crear conexion.
    - llamado desde lista de conexiones en caso tal que el usuario desee
    crear una nueva conexion.

    TODO REVIEW
    """
    model = Connection
    login_url = '/accounts/login/'
    fields = []
    template_name = 'connection/create.html'
    success_url = ''

    def get_success_url(self):
        if 'plug_type' in self.request.session:
            plug_type = self.request.session['plug_type']
        else:
            plug_type = 'source'
        return reverse('connection:list', kwargs={'connector_id': self.kwargs['connector_id'], 'type': plug_type})

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
            elif connector in [ConnectorEnum.GoogleSpreadSheets, ConnectorEnum.GoogleContacts, ConnectorEnum.YouTube,
                               ConnectorEnum.GoogleForms, ConnectorEnum.GoogleCalendar]:
                form.instance.credentials_json = self.request.session['google_credentials']
            elif connector == ConnectorEnum.Vtiger:
                controller_class = ConnectorEnum.get_controller(connector)
                controller = controller_class()
                token = controller.get_token(form.cleaned_data['connection_user'],
                                             form.cleaned_data['url'])
                form.instance.token = token
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
                self.template_name = 'connection/create/{0}.html'.format(connector.name.lower())
            elif connector.connection_type == 'authorization':
                self.template_name = 'connection/create_with_auth.html'
            self.request.session['connection_action'] = 'create'
        return super(CreateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
            self.model, self.fields = ConnectorEnum.get_connector_data(connector)
            if connector.connection_type == 'special':
                self.template_name = 'connection/create/{0}.html'.format(connector.name.lower())
            elif connector.connection_type == 'authorization':
                self.template_name = 'connection/create_with_auth.html'
            if 'connection_action' in self.request.session:
                del self.request.session['connection_action']
            if 'connection_id' in self.request.session:
                del self.request.session['connection_id']
        return super(CreateConnectionView, self).post(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        connector = ConnectorEnum.get_connector(self.kwargs['connector_id'])
        context = super(CreateConnectionView, self).get_context_data(**kwargs)
        context['connection'] = connector.name
        context['connector_name'] = connector.name
        context['connector_id'] = connector.value
        if connector in [ConnectorEnum.GoogleSpreadSheets, ConnectorEnum.GoogleForms, ConnectorEnum.GoogleContacts,
                         ConnectorEnum.GoogleCalendar, ConnectorEnum.YouTube, ConnectorEnum.Gmail]:
            api = GoogleAPIEnum.get_api(connector.name)
            flow = get_flow(settings.GOOGLE_AUTH_CALLBACK_URL, scope=api.scope)
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = api.name.lower()
        elif connector == ConnectorEnum.Slack:
            context['authorization_url'] = settings.SLACK_PERMISSIONS_URL + '&redirect_uri={0}{1}'.format(
                settings.CURRENT_HOST, reverse('connection:slack_auth'))
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
            request_token = client.get_request_token(settings.EVERNOTE_REDIRECT_URL)
            self.request.session['oauth_secret_evernote'] = request_token['oauth_token_secret']
            context['authorization_url'] = client.get_authorize_url(request_token)
        elif connector == ConnectorEnum.Asana:
            oauth = OAuth2Session(client_id=settings.ASANA_CLIENT_ID, redirect_uri=settings.ASANA_REDIRECT_URL)
            authorization_url, state = oauth.authorization_url(
                'https://app.asana.com/-/oauth_authorize?response_type=code&client_id={0}&redirect_uri={1}&state=1234'.format(
                    settings.ASANA_CLIENT_ID, settings.ASANA_REDIRECT_URL))
            context['authorization_url'] = authorization_url
        elif connector == ConnectorEnum.MercadoLibre:
            m = MercadolibreClient(client_id=settings.MERCADOLIBRE_CLIENT_ID,
                                   client_secret=settings.MERCADOLIBRE_CLIENT_SECRET)
            context['authorization_url'] = m.authorization_url(redirect_uri=settings.MERCADOLIBRE_REDIRECT_URL)
            context['sites'] = MercadoLibreConnection.SITES
        elif connector == ConnectorEnum.WunderList:
            oauth = OAuth2Session(client_id=settings.WUNDERLIST_CLIENT_ID,
                                  redirect_uri=settings.WUNDERLIST_REDIRECT_URL)
            url, state = oauth.authorization_url('https://www.wunderlist.com/oauth/authorize?state=RANDOM')
            context['authorization_url'] = url
        elif connector == ConnectorEnum.MailChimp:
            context['authorization_url'] = get_mailchimp_url()
        elif connector == ConnectorEnum.FacebookLeads:
            context['app_id'] = settings.FACEBOOK_APP_ID
        elif connector == ConnectorEnum.GitLab:
            oauth = OAuth2Session(client_id=settings.GITLAB_CLIENT_ID, redirect_uri=settings.GITLAB_REDIRECT_URL)
            authorization_url, state = oauth.authorization_url(
                'https://gitlab.com/oauth/authorize?response_type=code&client_id={0}&redirect_uri={1}&state=1234'.format(
                    settings.GITLAB_CLIENT_ID, settings.GITLAB_REDIRECT_URL))
            context['authorization_url'] = authorization_url
        elif connector == ConnectorEnum.InfusionSoft:
            data = {
                "client_id": settings.INFUSIONSOFT_CLIENT_ID,
                "redirect_uri": settings.INFUSIONSOFT_REDIRECT_URL,
                "response_type": "code",
                "scope": "full|gn389.infusionsoft.com"
            }
            authorization_url = '%s%s' % (settings.INFUSIONSOFT_AUTHORIZATION_URL, urlencode(data))
            context['authorization_url'] = authorization_url
        elif connector == ConnectorEnum.TypeForm:
            data = {
                "client_id": settings.TYPEFORM_CLIENT_ID,
                "redirect_uri": settings.TYPEFORM_REDIRECT_URL,
                "scope": settings.TYPEFROM_SCOPES
            }
            authorization_url = '%s%s' % (settings.TYPEFORM_AUTHORIZATION_URL, urlencode(data))
            context['authorization_url'] = authorization_url
        return context


class CreateConnectionSuccessView(LoginRequiredMixin, TemplateView):
    """
    template para cerrar la vnetana al terminar el auth??
    """
    template_name = 'connection/success_close.html'
    login_url = '/accounts/login/'


class CreateTokenAuthorizedConnectionView(TemplateView):
    template_name = 'connection/auth_success.html'

    def get(self, request, **kwargs):
        if 'connection_data' in self.request.session:
            data = self.request.session['connection_data']
            connector = ConnectorEnum.get_connector(name=self.request.session['connector_name'])
            connector_model = ConnectorEnum.get_model(connector)
            if 'connection_action' in self.request.session and self.request.session['connection_action'] == 'update':
                c = Connection.objects.get(pk=self.request.session['connection_id'])
                saved_keys = []
                for k, v in data.items():
                    if hasattr(c.related_connection, k):
                        saved_keys.append(k)
                        setattr(c.related_connection, k, v)
                c.related_connection.save()
            else:
                c = Connection.objects.create(user=request.user, connector_id=connector.value)
                n = int(connector_model.objects.filter(connection__user=request.user).count()) + 1
                data['connection_id'] = c.id
                data['name'] = "{0} Connection # {1}".format(connector.name, n)
                try:
                    obj = connector_model.objects.create(**data)
                except Exception:
                    # TODO: Connection Error
                    pass
            return redirect(self.get_success_url())

    def get_success_url(self):
        if 'plug_type' in self.request.session:
            plug_type = self.request.session['plug_type']
        else:
            plug_type = 'source'
        return reverse('connection:list', kwargs={
            'connector_id': ConnectorEnum.get_connector(name=self.request.session['connector_name']).value,
            'type': plug_type})


class AuthSuccess(TemplateView):
    template_name = 'connection/auth_success.html'


class TestConnectionView(LoginRequiredMixin, View):
    """
        Test generic connections without saving any 
        actual connection to the database.
    """

    def post(self, request, **kwargs):
        try:
            connector = ConnectorEnum.get_connector(kwargs['connector_id'])
            if 'connection_id' in request.POST:
                connection_object = Connection.objects.get(
                    pk=request.POST['connection_id']).related_connection
                controller_class = ConnectorEnum.get_controller(connector)
                controller = controller_class(connection=connection_object)
            else:
                connection_model = ConnectorEnum.get_model(connector)
                connection_params = {key: str(val) for key, val in request.POST.items()}
                del (connection_params['csrfmiddlewaretoken'])  # Eliminar csrf token de los parametros
                connection_object = connection_model(**connection_params)
                controller_class = ConnectorEnum.get_controller(connector)
                controller = controller_class(connection=connection_object)
            return JsonResponse({'test': controller.test_connection()})
        except Exception as e:
            # raise
            return JsonResponse({'test': False})


# Auth Views

class FacebookAuthView(View):
    def get(self, request, *args, **kwargs):
        print(request.GET)


class MercadoLibreAuthView(View):
    def get(self, request, *args, **kwargs):
        m = MercadolibreClient(client_id=settings.MERCADOLIBRE_CLIENT_ID,
                               client_secret=settings.MERCADOLIBRE_CLIENT_SECRET)
        token = m.exchange_code(code=request.GET.get('code'), redirect_uri=settings.MERCADOLIBRE_REDIRECT_URL)
        m.set_token(token)
        user_me = m.me()
        user_id = user_me['id']
        site_id = 'MLC'
        request.session['connection_data'] = {'token': token, 'site': site_id, 'user_id': user_id}
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
            auth_client = slack.oauth.access(
                client_id=settings.SLACK_CLIENT_ID,
                client_secret=settings.SLACK_CLIENT_SECRET, code=code,
                redirect_uri=settings.CURRENT_HOST + reverse(
                    'connection:slack_auth'))
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
        return redirect(
            reverse('connection:create_token_authorized_connection'))


class AsanaAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        oauth = OAuth2Session(client_id=settings.ASANA_CLIENT_ID,
                              redirect_uri=settings.ASANA_REDIRECT_URL)
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


class TypeFormAuthView(View):
    def get(self, request, *args, **kwargs):
        auth_code = request.GET.get('code', None)
        data = {'client_id': settings.TYPEFORM_CLIENT_ID,
                'client_secret': settings.TYPEFORM_CLIENT_SECRET,
                'code': auth_code,
                'redirect_uri': settings.TYPEFORM_REDIRECT_URL}
        url = "https://api.typeform.com/oauth/token"
        response = requests.post(url, data=data).json()
        self.request.session['connection_data'] = {'token': response["access_token"], }
        self.request.session['connector_name'] = ConnectorEnum.TypeForm.name
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
            self.request.session['connection_data'] = {'token': response['access_token'], 'shop_url': shop_url}
            self.request.session['connector_name'] = ConnectorEnum.Shopify.name
            return redirect(reverse('connection:create_token_authorized_connection'))
        except Exception as e:
            raise
        # TODO: error
        return redirect(reverse('connection:shopify_success_create_connection'))


class GitLabAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        oauth = OAuth2Session(client_id=settings.GITLAB_CLIENT_ID, redirect_uri=settings.GITLAB_REDIRECT_URL)
        token = oauth.fetch_token('https://gitlab.com/oauth/token', code=code,
                                  authorization_response=settings.GITLAB_REDIRECT_URL,
                                  client_id=settings.GITLAB_CLIENT_ID, client_secret=settings.GITLAB_CLIENT_SECRET, )
        self.request.session['connection_data'] = {'token': token['access_token'],
                                                   'refresh_token': token['refresh_token']}
        self.request.session['connector_name'] = ConnectorEnum.GitLab.name
        return redirect(reverse('connection:create_token_authorized_connection'))


class MailchimpAuthView(View):
    def get(self, request, *args, **kwargs):
        auth_code = request.GET.get('code', None)
        data = {"grant_type": "authorization_code", "client_id": settings.MAILCHIMP_CLIENT_ID, "code": auth_code,
                "client_secret": settings.MAILCHIMP_CLIENT_SECRET, "redirect_uri": settings.MAILCHIMP_REDIRECT_URL}
        url = settings.MAILCHIMP_ACCESS_TOKEN_URI
        response = requests.post(url, data=data).json()
        print(response.text)
        try:
            self.request.session['connection_data'] = {'token': response["access_token"]}
            self.request.session['connector_name'] = ConnectorEnum.MailChimp.name
        except:
            raise
        return redirect(reverse('connection:create_token_authorized_connection'))


class InfusionSoftAuthView(View):
    def get(self, request, *args, **kwargs):
        code = request.GET.get('code', '')
        oauth = OAuth2Session(client_id=settings.INFUSIONSOFT_CLIENT_ID,
                              redirect_uri=settings.INFUSIONSOFT_REDIRECT_URL)
        token = oauth.fetch_token('https://api.infusionsoft.com/token',
                                  code=code,
                                  authorization_response=settings.INFUSIONSOFT_REDIRECT_URL,
                                  client_id=settings.INFUSIONSOFT_CLIENT_ID,
                                  client_secret=settings.INFUSIONSOFT_CLIENT_SECRET, )
        self.request.session['connection_data'] = {
            'token': token['access_token'],
            'refresh_token': token['refresh_token'],
            'token_expiration_time': token['expires_at']}
        print('data de conexion', self.request.session['connection_data'])
        self.request.session['connector_name'] = ConnectorEnum.InfusionSoft.name
        return redirect(
            reverse('connection:create_token_authorized_connection'))


# NPI
class AjaxMercadoLibrePostSiteView(View):
    def post(self, request, *args, **kwargs):
        request.session['mercadolibre_site'] = request.POST.get('site_id', None)
        return JsonResponse({'success': True})


def get_salesforce_auth():
    return 'https://login.salesforce.com/services/oauth2/authorize?response_type=code&client_id={}&redirect_uri={}'.format(
        settings.SALESFORCE_CLIENT_ID, settings.SALESFORCE_REDIRECT_URI)


def get_survey_monkey_url():
    url_params = urllib.parse.urlencode(
        {"redirect_uri": settings.SURVEYMONKEY_REDIRECT_URI,
         "client_id": settings.SURVEYMONKEY_CLIENT_ID,
         "response_type": "code"})
    return '{0}{1}?{2}'.format(settings.SURVEYMONKEY_API_BASE,
                               settings.SURVEYMONKEY_AUTH_CODE_ENDPOINT,
                               url_params)


def get_mailchimp_url():
    return 'https://login.mailchimp.com/oauth2/authorize?client_id={0}&redirect_uri={1}&response_type=code'.format(
        settings.MAILCHIMP_CLIENT_ID,
        settings.MAILCHIMP_REDIRECT_URL)


def get_shopify_url():
    return "https://{0}.myshopify.com/admin/oauth/authorize?client_id={1}&scope={2}&redirect_uri={3}".format(
        'xxxx', settings.SHOPIFY_API_KEY, settings.SHOPIFY_SCOPE,
        settings.SHOPIFY_REDIRECT_URI)


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


class ManageConnectionView(LoginRequiredMixin, ListView):
    model = Connection
    template_name = 'connection/manage.html'
    login_url = '/accounts/login/'

    def get_queryset(self):
        all_connections = self.model.objects.filter(user=self.request.user)
        connectors = []
        for connection in all_connections:
            if connection.connector.name.lower() not in connectors:
                connectors.append(connection.connector.name.lower())
        result = []
        for connector in connectors:
            result.append(
                all_connections.filter(connector__name__iexact=connector))
        return result


class UpdateConnectionView(UpdateView):
    model = Connection
    template_name = 'connection/update.html'
    fields = ['name', 'gear_group']
    login_url = '/accounts/login/'
    success_url = reverse_lazy('connection:create_success')

    def get(self, request, *args, **kwargs):
        if self.kwargs['pk'] is not None:
            connection = self.model.objects.get(pk=self.kwargs['pk'])
            connector = ConnectorEnum.get_connector(connection.connector.id)
            self.model, self.fields = ConnectorEnum.get_connector_data(
                connector)
            if connector.connection_type == 'special':
                self.template_name = 'connection/create/{0}.html'.format(
                    connector.name.lower())
            elif connector.connection_type == 'authorization':
                self.template_name = 'connection/create_with_auth.html'
            self.request.session['connection_action'] = 'update'
            self.request.session['connection_id'] = connection.id
        return super(UpdateConnectionView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if self.kwargs['pk'] is not None:
            connection = self.model.objects.get(pk=self.kwargs['pk'])
            connector = ConnectorEnum.get_connector(connection.connector.id)
            self.model, self.fields = ConnectorEnum.get_connector_data(
                connector)
            if 'connection_action' in self.request.session:
                del self.request.session['connection_action']
            if 'connection_id' in self.request.session:
                del self.request.session['connection_id']
        return super(UpdateConnectionView, self).post(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.model.objects.get(connection__id=self.kwargs['pk'])

    def get_context_data(self, *args, **kwargs):
        connection = self.model.objects.get(connection__id=self.kwargs['pk'])
        connector = ConnectorEnum.get_connector(
            connection.connection.connector.id)
        context = super(UpdateConnectionView, self).get_context_data(**kwargs)
        context['connection'] = connection.connection.id
        context['connector_name'] = connector.name
        context['connector_id'] = connector.value
        if connector in [ConnectorEnum.GoogleSpreadSheets, ConnectorEnum.GoogleForms, ConnectorEnum.GoogleContacts,
                         ConnectorEnum.GoogleCalendar, ConnectorEnum.YouTube, ConnectorEnum.Gmail]:
            api = GoogleAPIEnum.get_api(connector.name)
            flow = get_flow(settings.GOOGLE_AUTH_CALLBACK_URL, scope=api.scope)
            context['authorization_url'] = flow.step1_get_authorize_url()
            self.request.session['google_connection_type'] = api.name.lower()
        elif connector == ConnectorEnum.Slack:
            context['authorization_url'] = settings.SLACK_PERMISSIONS_URL + '&redirect_uri={0}{1}'.format(
                settings.CURRENT_HOST, reverse('connection:slack_auth'))
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
            request_token = client.get_request_token(settings.EVERNOTE_REDIRECT_URL)
            self.request.session['oauth_secret_evernote'] = request_token['oauth_token_secret']
            context['authorization_url'] = client.get_authorize_url(request_token)
        elif connector == ConnectorEnum.Asana:
            oauth = OAuth2Session(client_id=settings.ASANA_CLIENT_ID, redirect_uri=settings.ASANA_REDIRECT_URL)
            authorization_url, state = oauth.authorization_url(
                'https://app.asana.com/-/oauth_authorize?response_type=code&client_id={0}&redirect_uri={1}&state=1234'.format(
                    settings.ASANA_CLIENT_ID, settings.ASANA_REDIRECT_URL))
            context['authorization_url'] = authorization_url
        elif connector == ConnectorEnum.MercadoLibre:
            m = MercadolibreClient(client_id=settings.MERCADOLIBRE_CLIENT_ID,
                                   client_secret=settings.MERCADOLIBRE_CLIENT_SECRET)
            context['authorization_url'] = m.authorization_url(redirect_uri=settings.MERCADOLIBRE_REDIRECT_URL)
            context['sites'] = MercadoLibreConnection.SITES
        elif connector == ConnectorEnum.WunderList:
            oauth = OAuth2Session(client_id=settings.WUNDERLIST_CLIENT_ID,
                                  redirect_uri=settings.WUNDERLIST_REDIRECT_URL)
            url, state = oauth.authorization_url('https://www.wunderlist.com/oauth/authorize?state=RANDOM')
            context['authorization_url'] = url
        elif connector == ConnectorEnum.MailChimp:
            context['authorization_url'] = get_mailchimp_url()
        elif connector == ConnectorEnum.FacebookLeads:
            context['app_id'] = settings.FACEBOOK_APP_ID
        elif connector == ConnectorEnum.GitLab:
            oauth = OAuth2Session(client_id=settings.GITLAB_CLIENT_ID, redirect_uri=settings.GITLAB_REDIRECT_URL)
            authorization_url, state = oauth.authorization_url(
                'https://gitlab.com/oauth/authorize?response_type=code&client_id={0}&redirect_uri={1}&state=1234'.format(
                    settings.GITLAB_CLIENT_ID, settings.GITLAB_REDIRECT_URL))
            context['authorization_url'] = authorization_url
        return context


def get_gears_from_connection(request):
    if request.is_ajax() is True and request.method == 'POST':
        connection_id = request.POST.get('connection_id', None)
        gears = Gear.objects.filter(Q(source__connection_id=connection_id) | Q(target__connection_id=connection_id))
        template = loader.get_template('connection/snippets/menu_gears.html')
        context = {'gears': gears}
        return JsonResponse({'data': True, 'html': template.render(context)})
    return JsonResponse({'data': False})
