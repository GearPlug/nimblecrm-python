from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.urls import reverse_lazy
from apps.connection.apps import APP_NAME as app_name
from apps.gp.models import Connection, Connector, StoredData, FacebookConnection, GearMap, Gear, GearMapData, Plug
from apps.gp.enum import ConnectorEnum
from apps.gp.views import TemplateViewWithPost

# IMPORT CENTRALIZADO
from apps.connection.myviews.FacebookViews import AJAXFacebookBaseView, AJAXFacebookGetAvailableConnectionsView, \
    AJAXFacebookGetAvailableFormsView, AJAXFacebookGetAvailableLeadsView, extend_facebook_token, facebook_request
from apps.connection.myviews.MySQLViews import AJAXMySQLTestConnection


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
            if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Facebook:
                token = self.request.POST.get('token', '')
                long_user_access_token = extend_facebook_token(token)
                pages = facebook_request('me/accounts', long_user_access_token)
                page_token = None
                for page in pages:
                    if page['id'] == form.instance.id_page:
                        page_token = page['access_token']
                        break
                if page_token:
                    form.instance.token = page_token
                self.fetch_facebook_leads(form.instance)
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

    def fetch_facebook_leads(self, facebook_connection, *args, **kwargs):
        leads = facebook_request('%s/leads' % facebook_connection.id_form, facebook_connection.token)
        stored_data = [(item.connection, item.object_id, item.name) for item in
                       StoredData.objects.filter(connection=facebook_connection.connection)]
        new_data = []
        for item in leads:
            new_data = new_data + [StoredData(name=lead['name'], value=lead['values'][0], object_id=item['id'],
                                              connection=facebook_connection.connection)
                                   for lead in item['field_data']
                                   if (facebook_connection.connection, item['id'], lead['name']) not in stored_data]
        StoredData.objects.bulk_create(new_data)


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
            print(stored)
            map_data = GearMapData.objects.filter(gear_map=map)
            print(map_data)
            values_list = {data.target_name: data.source_value for data in map_data}
            data_list = []
            for item in stored:
                if item.name in values_list.keys():
                    final_value = values_list[item.name].replace('%%%%%s%%%%' % item.name, '%%%s%%' % item.value)
                    data_list.append(final_value)
            print(data_list)
        context['fb_data'] = []
        return context
