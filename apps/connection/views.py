from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from apps.api.views import mysql_get_insert_values, mysql_trigger_create_row
from apps.connection.apps import APP_NAME as app_name
from apps.connection.myviews.FacebookViews import *
from apps.connection.myviews.MySQLViews import *
from apps.connection.myviews.SugarCRMViews import *
from apps.connection.myviews.MailChimpViews import *
from apps.gp.controllers import FacebookController
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Connection, Connector, StoredData, GearMap, GearMapData
from apps.gp.views import TemplateViewWithPost

fbc = FacebookController()


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

    def form_invalid(self, form, *args, **kwargs):
        return super(CreateConnectionView, self).form_invalid(form, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        if self.kwargs['connector_id'] is not None:
            c = Connection.objects.create(user=self.request.user, connector_id=self.kwargs['connector_id'])
            form.instance.connection = c
            if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Facebook:
                token = self.request.POST.get('token', '')
                long_user_access_token = fbc.extend_token(token)
                pages = fbc.get_pages(long_user_access_token)
                page_token = None
                for page in pages:
                    if page['id'] == form.instance.id_page:
                        page_token = page['access_token']
                        break
                if page_token:
                    form.instance.token = page_token
                # fbc.download_leads_to_stored_data(form.instance)
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


class ListConnectorView(ListView):
    model = Connector
    template_name = '%s/list_connector.html' % app_name


class TestConnectionView(TemplateViewWithPost):
    template_name = 'test.html'

    def get_context_data(self, *args, **kwargs):
        context = super(TestConnectionView, self).get_context_data(**kwargs)
        map_list = GearMap.objects.filter(is_active=True, gear__is_active=True) \
            .select_related('gear__source', 'gear__target', )
        for map in map_list:
            stored = StoredData.objects.filter(connection=map.gear.source.connection)
            target_data = {data.target_name: data.source_value for data in GearMapData.objects.filter(gear_map=map)}
            source_data = [
                {'id': item[0], 'data': {i.name: i.value for i in stored.filter(object_id=item[0])}}
                for item in stored.values_list('object_id').distinct()]
            connection = Connection.objects.get(plug=map.gear.target)
            # Validar el conector del target para obtener el objeto o los objetos a enviar.
            columns, insert_values = mysql_get_insert_values(source_data, target_data, connection.related_connection)
            mysql_trigger_create_row(connection.related_connection, columns, insert_values)
        context['fb_data'] = []
        return context
