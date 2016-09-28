from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView

from apps.gear.apps import APP_NAME as app_name
from apps.gear.forms import MapForm
from apps.gp.controllers import MySQLController, SugarCRMController
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Gear, Plug, StoredData, GearMap, GearMapData
from apps.gp.views import TemplateViewWithPost

mysqlc = MySQLController()
scrmc = SugarCRMController()


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
        self.source_object_list = self.get_available_source_fields(source_plug)
        self.form_field_list = self.get_target_field_list(target_plug)
        # print(self.source_object_list)
        # print(self.form_field_list)
        return super(CreateGearMapView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        gear_id = kwargs.pop('gear_id', 0)
        gear = Gear.objects.filter(pk=gear_id).select_related('source', 'target').get(pk=gear_id)
        target_plug = Plug.objects.filter(pk=gear.target.id).select_related('connection__connector').get(
            pk=gear.target.id)
        self.form_field_list = self.get_target_field_list(target_plug)
        return super(CreateGearMapView, self).post(request, *args, **kwargs)

    def form_valid(self, form, *args, **kwargs):
        map = GearMap.objects.create(gear_id=self.kwargs['gear_id'], is_active=True)
        map.gear.is_active = True
        map.gear.save()
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

    def get_available_source_fields(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        fields = ConnectorEnum.get_fields(c)
        related = plug.connection.related_connection
        connection_data = {}
        for field in fields:
            connection_data[field] = getattr(related, field) if hasattr(related, field) else ''
        return ['%%%%%s%%%%' % item['name'] for item in self.get_source_data_list(plug, plug.connection)]

    def get_target_field_list(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        fields = ConnectorEnum.get_fields(c)
        related = plug.connection.related_connection
        connection_data = {}
        for field in fields:
            connection_data[field] = getattr(related, field) if hasattr(related, field) else ''
        if c == ConnectorEnum.MySQL:
            mysqlc.create_connection(host=connection_data['host'], port=int(connection_data['port']),
                                     connection_user=connection_data['connection_user'],
                                     connection_password=connection_data['connection_password'],
                                     database=connection_data['database'], table=connection_data['table'])
            form_data = mysqlc.describe_table()
            return [item['name'] for item in form_data if item['is_primary'] is not True]
        elif c == ConnectorEnum.SugarCRM:
            ping = scrmc.create_connection(url=connection_data['url'],
                                           connection_user=connection_data['connection_user'],
                                           connection_password=connection_data['connection_password'])
            try:
                return scrmc.get_module_fields(plug.plug_specification.all()[0].value, get_structure=True)
            except:
                return []
        elif c == ConnectorEnum.MailChimp:
            pass
        else:
            return []

    def get_source_data_list(self, plug, connection):
        return StoredData.objects.filter(plug=plug, connection=connection).values('name').distinct()


class GearMapGetSourceData(TemplateViewWithPost):
    pass


class GearMapSendTargetData(TemplateViewWithPost):
    pass
