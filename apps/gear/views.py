from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.urls import reverse_lazy
from apps.gear.apps import APP_NAME as app_name
from apps.gp.models import Gear, Plug, PlugSpecification, StoredData
from apps.gear.forms import MapForm
from apps.gp.enum import ConnectorEnum
from apps.connection.myviews.FacebookViews import facebook_request
import MySQLdb


class ListGearView(ListView):
    model = Gear
    template_name = '%s/list.html' % app_name

    def get_context_data(self, **kwargs):
        context = super(ListGearView, self).get_context_data(**kwargs)
        return context


class CreateGearView(CreateView):
    model = Gear
    fields = ['name', ]
    template_name = '%s/create.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(CreateGearView, self).form_valid(form)

    def get(self, *args, **kwargs):
        return super(CreateGearView, self).get(*args, **kwargs)


class UpdateGearView(UpdateView):
    model = Gear
    fields = ['name', 'source', 'target']
    template_name = '%s/update.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class DeleteGearView(DeleteView):
    model = Gear
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class CreateGearMapView(FormView):
    template_name = 'gear/map/create.html'
    form_class = MapForm
    form_field_list = []

    def get(self, request, *args, **kwargs):
        gear_id = kwargs.pop('gear_id', 0)
        gear = Gear.objects.filter(pk=gear_id).select_related('source', 'target').get(pk=gear_id)
        source_plug = Plug.objects.filter(pk=gear.source.id).select_related('connection__connector').get(
            pk=gear.source.id)
        target_plug = Plug.objects.filter(pk=gear.target.id).select_related('connection__connector').get(
            pk=gear.target.id)
        self.plug_as_target(target_plug)
        self.plug_as_source(source_plug)
        return super(CreateGearMapView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return super(CreateGearMapView, self).post(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def form_invalid(self, form, *args, **kwargs):
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateGearMapView, self).get_context_data(**kwargs)
        return context

    def get_form(self, *args, **kwargs):
        kwargs['extra'] = self.form_field_list
        return self.form_class(**kwargs)

    # asigna la lista de objetos del source
    def plug_as_source(self, plug, *args, **kwargs):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        fields = ConnectorEnum.get_fields(c)
        related = plug.connection.related_connection
        connection_data = {}
        for field in fields:
            if hasattr(related, field):
                connection_data[field] = getattr(related, field)
            else:
                connection_data[field] = ''
        target_data_list = self.get_source_data_list(c, plug, connection_data)
        # print(target_data_list)
        item_list = []
        for item in target_data_list:
            for lead in item['field_data']:
                item_list.append(
                    StoredData(plug=plug, name=lead['name'], value=lead['values'][0], object_id=item['id']))
        print(item_list)

    # Modifica el formulario para target.
    def plug_as_target(self, plug, *args, **kwargs):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        fields = ConnectorEnum.get_fields(c)
        related = plug.connection.related_connection
        connection_data = {}
        for field in fields:
            if hasattr(related, field):
                connection_data[field] = getattr(related, field)
            else:
                connection_data[field] = ''
        form_data = self.get_mysql_table_info(c, plug, connection_data)
        self.form_field_list = []
        for item in form_data:
            self.form_field_list.append(item['name'])

    def get_source_data_list(self, Connector, plug, connection_data):
        if Connector == ConnectorEnum.Facebook:
            print("f")
            url = '%s/leads' % connection_data['id_form']
            token = connection_data['token']
            return facebook_request(url, token)
        return []

    def get_mysql_table_info(self, Connector, plug, connection_data):
        table_data = []
        try:
            con = MySQLdb.connect(host=connection_data['host'], port=int(connection_data['port']),
                                  user=connection_data['connection_user'],
                                  passwd=connection_data['connection_password'],
                                  db=connection_data['database'])
        except:
            con = None
            print("Error reaching the database")
        if con:
            try:
                cursor = con.cursor()
                ps = PlugSpecification.objects.get(plug=plug, action_specification__name='table name')
                # cursor.execute('USE %s' % connection_data['database'])
                cursor.execute('DESCRIBE `%s`.`%s`' % (connection_data['database'], ps.value))
                for item in cursor:
                    table_data.append(
                        {'name': item[0], 'type': item[1], 'null': 'YES' == item[2], 'is_primary': item[3] == 'PRI'})
            except Exception as e:
                print(e)
        return table_data
