from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.urls import reverse_lazy
from apps.connection.apps import APP_NAME as app_name
from apps.gp.models import Connection, Connector, FacebookConnection, MySQLConnection
from apps.gp.connector_enum import ConnectorEnum
import requests
from apiconnector.settings import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_GRAPH_VERSION
import hmac
import facebook
import hashlib
import json


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


class AJAXFacebookGetAvailableConnectionsView(TemplateView):
    template_name = 'ajax_response.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TestConnectionView, self).get_context_data(**kwargs)
        print(kwargs)
        token = ''
        graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)  # Crea el objeto para interactuar con GRAPH API
        graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)  # ACCESS TOKEN DE LA APP
        r = requests.get('https://graph.facebook.com/v%s/me/accounts' % FACEBOOK_GRAPH_VERSION,
                         params={'access_token': token,
                                 'appsecret_proof': generate_app_secret_proof(FACEBOOK_APP_SECRET,
                                                                              token)})
        fb_conn_list = json.loads(r.text)['data']
        return context


class TestConnectionView(TemplateView):
    template_name = 'test.html'

    def get_context_data(self, *args, **kwargs):
        connection_id = 1
        context = super(TestConnectionView, self).get_context_data(**kwargs)
        facebook_connection = FacebookConnection.objects.get(pk=connection_id)

        graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)  # Crea el objeto para interactuar con GRAPH API
        graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)  # ACCESS TOKEN DE LA APP

        try:
            # r = requests.get('https://graph.facebook.com/v%s/oauth/access_token' % FACEBOOK_GRAPH_VERSION,
            #                  params={'grant_type': 'fb_exchange_token', 'client_id': FACEBOOK_APP_ID,
            #                          'client_secret': FACEBOOK_APP_SECRET,
            #                          'fb_exchange_token': facebook_connection.token})

            # PIDE LAS CONNECTIONS ASOCIADAS AL USER. USA EL TOKEN DEL USUARIO Y EL SECRET ES USERTOKEN+APPSECRET
            r = requests.get('https://graph.facebook.com/v%s/me/accounts' % FACEBOOK_GRAPH_VERSION,
                             params={'access_token': facebook_connection.token,
                                     'appsecret_proof': generate_app_secret_proof(FACEBOOK_APP_SECRET,
                                                                                  facebook_connection.token)})
            fb_conn_list = json.loads(r.text)['data']
            fconn_list = []
            npi_list = []
            for form in fb_conn_list:
                fconn_list.append({'id': form['id'], 'name': form['name']})
                r2 = requests.get(
                    'https://graph.facebook.com/v%s/%s/leadgen_forms' % (FACEBOOK_GRAPH_VERSION, form['id']),
                    params={'access_token': facebook_connection.token,
                            'appsecret_proof': generate_app_secret_proof(FACEBOOK_APP_SECRET,
                                                                         facebook_connection.token)})
                npi_list.append(json.loads(r2.text)['data'])
            form_list = []
            for item in npi_list:
                for f in item:
                    form_list.append({'id': f['id'], 'name': f['name'], 'page_id': f['page_id']})

            # print(form_list)
            context['conn_list'] = fconn_list
            context['form_list'] = form_list
        except Exception as e:
            print(e)
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
        print(form.instance.token)
        return super(AJAXSetUserFacebookToken, self).form_valid(form, *args, **kwargs)

    def form_invalid(self, form, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).form_valid(form, *args, **kwargs)

    def post(self, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).post(*args, **kwargs)

    def get(self, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).get(*args, **kwargs)



def generate_app_secret_proof(app_secret, access_token):
    h = hmac.new(
        app_secret.encode('utf-8'),
        msg=access_token.encode('utf-8'),
        digestmod=hashlib.sha256
    )
    return h.hexdigest()
