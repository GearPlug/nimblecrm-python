from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.urls import reverse_lazy
from apps.connection.apps import APP_NAME as app_name
from apps.gp.models import Connection, Connector, FacebookConnection, MySQLConnection
from apps.gp.connector_enum import ConnectorEnum
from django.http import JsonResponse
import facebook
import requests
from apiconnector.settings import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_GRAPH_VERSION
import hmac
import hashlib


class ListConnectionView(ListView):
    model = Connection
    template_name = '%s/list.html' % app_name

    def get_context_data(self, **kwargs):
        context = super(ListConnectionView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class CreateConnectionView(CreateView):
    model = Connection
    fields = []
    template_name = '%s/create.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def form_valid(self, form, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            c = Connection.objects.create(user=self.request.user, connector_id=self.kwargs['connector_id'])
            form.instance.connection = c
            return super(CreateConnectionView, self).form_valid(form)

    def get(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
        return super(CreateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
        return super(CreateConnectionView, self).post(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateConnectionView, self).get_context_data(**kwargs)
        context['connection'] = ConnectorEnum.get_connector(self.kwargs['connector_id']).name
        return context


class UpdateConnectionView(UpdateView):
    model = Connection
    fields = []
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    # def get(self, *args, **kwargs):
    #     if self.kwargs['connector_id'] is not None:
    #         self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
    #     return super(CreateConnectionView, self).get(*args, **kwargs)
    #
    # def post(self, *args, **kwargs):
    #     if self.kwargs['connector_id'] is not None:
    #         self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
    #     return super(CreateConnectionView, self).post(*args, **kwargs)


class DeleteConnectionView(DeleteView):
    model = Connection
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class ListConnectorView(ListView):
    model = Connector
    template_name = '%s/list_connector.html' % app_name


class GenerateAppToken(TemplateView):
    template_name = 'test.html'

    def get(self, request, *args, **kwargs):
        return super(GenerateAppToken, )


class TestConnectionView(TemplateView):
    template_name = 'test.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TestConnectionView, self).get_context_data(**kwargs)
        r = requests.get('https://graph.facebook.com/oauth/access_token',
                         params={'client_id': FACEBOOK_APP_ID, 'client_secret': FACEBOOK_APP_SECRET,
                                 'grant_type': 'client_credentials'})
        if r.status_code == 200:
            token = r.text.split('=')[1]
            # print(token)
        else:
            token = None
        if token is not None:
            con = FacebookConnection.objects.values('token').get(pk=1)
            print(con['token'])
            graph = facebook.GraphAPI(access_token=con['token'], version=FACEBOOK_GRAPH_VERSION)
            access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, False)
            print(access_token)
            appsecret_proof = hmac.new(bytes(FACEBOOK_APP_SECRET.encode()), con['token'].encode(),
                                       hashlib.sha256).hexdigest()
            form = graph.get_object(id='1712285499010965', appsecret_proof=appsecret_proof)
            # form = graph.get_connections(id='me', connection_name='friends', appsecret_proof=appsecret_proof)
            print('form')
            print(form)
        # r2 = requests.get('https://graph.facebook.com/v2.6/%s/leads' % '1712285499010965',
        #                   params={'appsecret_proof': token})
        # print(r2.status_code)
        context['data'] = 'hola'
        return context


class AJAXSetUserFacebookToken(UpdateView):
    template_name = 'connection/update.html'
    model = FacebookConnection
    fields = ['token', ]
    success_url = reverse_lazy('%s:list' % app_name)

    def dispatch(self, request, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        print('valid')
        return super(AJAXSetUserFacebookToken, self).form_valid(form, *args, **kwargs)

    def form_invalid(self, form, *args, **kwargs):
        print('invalid')
        return super(AJAXSetUserFacebookToken, self).form_valid(form, *args, **kwargs)

    def post(self, *args, **kwargs):
        if self.request.is_ajax():
            self.success_url = '/'
        return super(AJAXSetUserFacebookToken, self).post(*args, **kwargs)

    def get(self, *args, **kwargs):
        print("get")
        return super(AJAXSetUserFacebookToken, self).get(*args, **kwargs)
