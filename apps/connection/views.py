from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from apps.connection.apps import APP_NAME as app_name
from apps.gp.models import Connection, Connector, FacebookConnection, MySQLConnection
from apps.gp.connector_enum import ConnectorEnum
import requests
from apiconnector.settings import FACEBOOK_APP_ID, FACEBOOK_APP_SECRET, FACEBOOK_GRAPH_VERSION
import hmac
import facebook
import hashlib
import json
import MySQLdb


class ListConnectionView(ListView):
    model = Connection
    template_name = '%s/list.html' % app_name

    def get_context_data(self, **kwargs):
        context = super(ListConnectionView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).prefetch_related()


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
            self.template_name = '%s/%s/create.html' % (
                app_name, ConnectorEnum.get_connector(self.kwargs['connector_id']).name.lower())
        return super(CreateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
            self.template_name = '%s/%s/create.html' % (
                app_name, ConnectorEnum.get_connector(self.kwargs['connector_id']).name.lower())
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

    def get(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
        return super(UpdateConnectionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            self.model, self.fields = ConnectorEnum.get_connector_data(self.kwargs['connector_id'])
        return super(UpdateConnectionView, self).post(*args, **kwargs)


class DeleteConnectionView(DeleteView):
    model = Connection
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class ListConnectorView(ListView):
    model = Connector
    template_name = '%s/list_connector.html' % app_name


# Template sin form que acepta post
class TemplateViewWithPost(TemplateView):
    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        return super(TemplateView, self).render_to_response(context)


# Vista base de facebook. Hace request utilizando el graph api.
class AJAXFacebookBaseView(TemplateViewWithPost):
    template_name = 'connection/facebook/ajax_facebook_select.html'
    base_graph_url = 'https://graph.facebook.com'
    has_objects = False

    def get_context_data(self, *args, **kwargs):
        context = super(AJAXFacebookBaseView, self).get_context_data(**kwargs)
        token = self.request.POST.get('user_access_token', '')
        url = kwargs.pop('url', '')
        graph = facebook.GraphAPI(version=FACEBOOK_GRAPH_VERSION)  # Crea el objeto para interactuar con GRAPH API
        graph.access_token = graph.get_app_access_token(FACEBOOK_APP_ID, FACEBOOK_APP_SECRET)  # ACCESS TOKEN DE LA APP
        r = requests.get('%s/v%s/%s' % (self.base_graph_url, FACEBOOK_GRAPH_VERSION, url),
                         params={'access_token': token,
                                 'appsecret_proof': generate_app_secret_proof(FACEBOOK_APP_SECRET, token)})
        try:
            object_list = json.loads(r.text)['data']
            context['object_list'] = object_list
            self.has_objects = True
        except:
            print("Error en el request")
        return context


class AJAXFacebookGetAvailableConnectionsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'

    def get_context_data(self, *args, **kwargs):
        kwargs['url'] = 'me/accounts'
        context = super(AJAXFacebookGetAvailableConnectionsView, self).get_context_data(**kwargs)
        return context


class AJAXFacebookGetAvailableFormsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'

    def get_context_data(self, *args, **kwargs):
        connection_id = self.request.POST.get('connection_id', '')
        kwargs['url'] = '%s/leadgen_forms' % connection_id
        context = super(AJAXFacebookGetAvailableFormsView, self).get_context_data(**kwargs)
        return context


class AJAXFacebookGetAvailableLeadsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'
    get_data = False

    def get_context_data(self, *args, **kwargs):
        self.get_data = self.request.POST.get('get_data', False)
        form_id = self.request.POST.get('form_id', '')
        kwargs['url'] = '%s/leads' % form_id
        context = super(AJAXFacebookGetAvailableLeadsView, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        if self.get_data:
            return super(TemplateView, self).render_to_response(context)
        return JsonResponse({'data': self.has_objects})


class TestConnectionView(TemplateViewWithPost):
    template_name = 'test.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TestConnectionView, self).get_context_data(**kwargs)
        return context


# No se esta usando
class AJAXSetUserFacebookToken(UpdateView):
    template_name = 'connection/update.html'
    model = FacebookConnection
    fields = ['token', ]
    success_url = reverse_lazy('%s:list' % app_name)

    def dispatch(self, request, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).form_valid(form, *args, **kwargs)

    def form_invalid(self, form, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).form_valid(form, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).post(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(AJAXSetUserFacebookToken, self).get(*args, **kwargs)


class AJAXMySQLTestConnection(TemplateViewWithPost):
    template_name = 'test.html'

    def post(self, request, *args, **kwargs):
        connection_reached = False
        name = self.request.POST.get('name', 'nombre')
        host = self.request.POST.get('host', 'host')
        port = self.request.POST.get('port', 'puerto')
        database = self.request.POST.get('database', 'database')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        try:
            con = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=database)
            connection_reached = True
        except:
            print("Error reaching the database")
        return JsonResponse({'data': connection_reached})

    def get_context_data(self, **kwargs):
        context = super(AJAXMySQLTestConnection, self).get_context_data(**kwargs)
        return context


# Facebook
def generate_app_secret_proof(app_secret, access_token):
    h = hmac.new(
        app_secret.encode('utf-8'),
        msg=access_token.encode('utf-8'),
        digestmod=hashlib.sha256
    )
    return h.hexdigest()
