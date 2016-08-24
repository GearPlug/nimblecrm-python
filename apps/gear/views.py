from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.urls import reverse_lazy
from django.db.utils import IntegrityError
from apps.gear.apps import APP_NAME as app_name
from apps.gp.models import Gear, Plug, PlugSpecification, StoredData, GearMap, GearMapData
from apps.gear.forms import MapForm
from apps.gp.enum import ConnectorEnum
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
    source_object_list = []
    success_url = reverse_lazy('%s:list' % app_name)

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
        gear_id = kwargs.pop('gear_id', 0)
        gear = Gear.objects.filter(pk=gear_id).select_related('source', 'target').get(pk=gear_id)
        target_plug = Plug.objects.filter(pk=gear.target.id).select_related('connection__connector').get(
            pk=gear.target.id)
        self.plug_as_target(target_plug)
        form = self.get_form()
        return super(CreateGearMapView, self).post(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        print(form.cleaned_data)
        map = GearMap.objects.create(gear_id=self.kwargs['gear_id'], is_active=False)
        map_data = []
        for field in form:
            map_data.append(
                GearMapData(gear_map=map, target_name=field.name, source_value=form.cleaned_data[field.name]))
        GearMapData.objects.bulk_create(map_data)
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def form_invalid(self, form, *args, **kwargs):
        return super(CreateGearMapView, self).form_valid(form, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateGearMapView, self).get_context_data(**kwargs)
        context['source_object_list'] = self.source_object_list
        return context

    def get_form(self, *args, **kwargs):
        form_class = self.get_form_class()
        return form_class(extra=self.form_field_list, **self.get_form_kwargs())

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
        # print(connection_data)
        self.source_object_list = ['%%%%%s%%%%' % item['name'] for item in  # ==> %%field_name%%
                                   self.get_source_data_list(c, plug.connection, connection_data)]

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
        self.form_field_list = [item['name'] for item in form_data if item['is_primary'] is not True]

    def get_source_data_list(self, Connector, connection, connection_data):
        if Connector == ConnectorEnum.Facebook:
            return StoredData.objects.filter(connection=connection).values('name').distinct()
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
                # cursor.execute('USE %s' % connection_data['database'])
                cursor.execute('DESCRIBE `%s`.`%s`' % (connection_data['database'], connection_data['table']))
                for item in cursor:
                    table_data.append(
                        {'name': item[0], 'type': item[1], 'null': 'YES' == item[2], 'is_primary': item[3] == 'PRI'})
            except Exception as e:
                print(e)
        return table_data
