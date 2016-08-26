from django.views.generic import CreateView, UpdateView, DeleteView, ListView, TemplateView
from django.urls import reverse_lazy
from apps.connection.apps import APP_NAME as app_name
from apps.gp.models import Connection, Connector, StoredData, FacebookConnection, GearMap, Gear, GearMapData, Plug
from apps.gp.enum import ConnectorEnum
from apps.gp.views import TemplateViewWithPost
import re

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
            target_data = {data.target_name: data.source_value for data in GearMapData.objects.filter(gear_map=map)}

            source_data = [
                {'id': item[0], 'data': {i.name: i.value for i in stored.filter(object_id=item[0])}}
                for item in stored.values_list('object_id').distinct()]

            sql_insert_list = self.get_mysql_inserts(source_data, target_data, 'puta')
            print(sql_insert_list)

            # for item in data_dict:
            #     sql_values = []
            #     for i, field in enumerate(item['data']):
            #         if field in values_list.keys():
            #             sql_values += '"%s"' % item['data'][field]
            #             if i < len(item['data']) - 1:
            #                 sql_values += ', '
            # print(sql_insert)
            # print(sql_values)
            #     print(item['data'])
            #     # INSERT INTO `apiConnector-00`.`test_save_leads` (`id`, `first_name`, `last_name`, `problem`, `extra_data`) VALUES ('', '2', '3', '4', '5');
            #     table_info = table_info + ''

            # print(data_dict)
            # for item in stored:
            #     if item.name in values_list.keys():
            #         data_dict[str(item.id)][item.name] = values_list[item.name].replace('%%%%%s%%%%' % item.name,
            #                                                                             item.value)
            # print(data_dict)
        context['fb_data'] = []
        return context

    def get_mysql_inserts(self, source_data, target_data, table, *args, **kwargs):
        sql_table_name = table
        sql_base_values = []
        sql_table_info = []
        for i, field in enumerate(target_data):
            sql_table_info.append('"%s"' % field)
            sql_base_values.append('"%s"' % target_data[field])

        sql_base_insert = 'INSERT INTO %s (%s) VALUES(%s)' % \
                          (sql_table_name, ','.join(sql_table_info), ','.join(sql_base_values))
        # print(target_data)
        sql_insert_list = []
        sublist = ['%%%%%s%%%%' % key for key in target_data]
        # print(sublist)
        pattern = re.compile(r'\b(' + '|'.join(sublist) + r'\b)')

        result = pattern.sub(lambda x: sublist[x.group()], sql_base_insert)

        final_data = [{attribute: {'%%%%%s%%%%' % a: item[attribute][a] for a in
                                   item[attribute]} if attribute == 'data' else item[attribute] for attribute in item}
                      for item in source_data]

        for item in final_data:
            # print(item['data'].keys())
            # for a in item['data']:
            #     print(re.escape(a))
            stri = '(%s)' % '|'.join([re.escape(a) for a in item['data']])
            pattern = re.compile(r'%s' % stri)
            result = pattern.sub(lambda x: item['data'][x.group()], sql_base_insert)
            print(stri)
            print(pattern)

        s = 'Hola soy german'
        d = {
            'Hola': 'chao',
            'soy': 'ya',
            'german': 'me voy'
        }

        pattern = re.compile(r'\b(' + '|'.join(d.keys()) + r')\b')
        result = pattern.sub(lambda x: d[x.group()], s)
        # print(result)
        # for item in source_data:
        #     print(item)
        
        #target_data = ['uno', 'dos', 'tres']
	    #sql_insert_base = 'INSERT INTO %s (%s) VALUES(%s)'%('tableA', ','.join(target_data), ','.join(['"%%%%%s%%%%"' % a for a in target_data]))
	    #d = {'%%uno%%': 'hola','%%dos%%': 'ya', '%%tres%%': 'me voy',}
	    #regex = '|'.join([re.escape('%%%%%s%%%%' % key) for key in target_data])
	    #regex_obj = re.compile(regex)
	    #print(regex)
	    #print(regex_obj)
	    #final = regex_obj.sub(lambda x: d[x.group()], sql_insert_base)
	    #print(final)
