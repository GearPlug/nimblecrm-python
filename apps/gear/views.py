import httplib2
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.http.response import JsonResponse
from apps.gear.apps import APP_NAME as app_name
from apps.gear.forms import MapForm
from apps.gp.controllers.database import MySQLController, PostgreSQLController, MSSQLController
from apps.gp.controllers.lead import GoogleFormsController, FacebookController
from apps.gp.controllers.crm import SugarCRMController
from apps.gp.controllers.email_marketing import MailChimpController, GetResponseController
from apps.gp.controllers.directory import GoogleContactsController
from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController, GoogleCalendarController
from apps.gp.controllers.im import SlackController
from apps.gp.controllers.social import TwitterController, YouTubeController
from apps.gp.controllers.im import SlackController, SMSController
from apps.gp.controllers.social import TwitterController
from apps.gp.controllers.project_management import JiraController
from apps.gp.controllers.repository import BitbucketController
from apps.gp.enum import ConnectorEnum
from apps.gp.map import MapField
from apps.gp.models import Gear, Plug, StoredData, GearMap, GearMapData
from apps.gp.views import TemplateViewWithPost
from oauth2client import client

mysqlc = MySQLController()
postgresqlc = PostgreSQLController()
mcc = MailChimpController()
mssqlc = MSSQLController()


class ListGearView(ListView):
    model = Gear
    template_name = '%s/list.html' % app_name

    def get_context_data(self, **kwargs):
        context = super(ListGearView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        queryset = self.model._default_manager.all()
        return queryset.filter(user=self.request.user)


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

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).prefetch_related()


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
    scrmc = SugarCRMController()
    gsc = GoogleSpreadSheetsController()
    slack_controller = SlackController()
    jirac = JiraController()
    bitbucketc = BitbucketController()
    google_contacts_controller = GoogleContactsController()
    getresponsec = GetResponseController()
    twitterc = TwitterController()
    gcc = GoogleCalendarController()
    youtubec = YouTubeController()
    smsc = SMSController()

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
        print(self.form_field_list)
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
        print("\n----------------------------\n")
        print(self.form_field_list)
        return form_class(extra=self.form_field_list, **self.get_form_kwargs())

    def get_available_source_fields(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        if c == ConnectorEnum.GoogleContacts:
            self.google_contacts_controller.create_connection(plug.connection.related_connection, plug)
            return ['%%%%%s%%%%' % field for field in self.google_contacts_controller.get_contact_fields()]
        # fields = ConnectorEnum.get_fields(c)
        # related = plug.connection.related_connection
        # connection_data = {}
        # for field in fields:
        #     connection_data[field] = getattr(related, field) if hasattr(related, field) else ''
        return ['%%%%%s%%%%' % item['name'] for item in self.get_source_data_list(plug, plug.connection)]

    def get_target_field_list(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        fields = ConnectorEnum.get_fields(c)
        controller_class = ConnectorEnum.get_controller(c)
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
            # print(form_data)
            return [item['name'] for item in form_data if item['is_primary'] is not True]
        elif c == ConnectorEnum.PostgreSQL:
            postgresqlc.create_connection(host=connection_data['host'], port=int(connection_data['port']),
                                          connection_user=connection_data['connection_user'],
                                          connection_password=connection_data['connection_password'],
                                          database=connection_data['database'], table=connection_data['table'])
            form_data = postgresqlc.describe_table()
            primary_keys = postgresqlc.get_primary_keys()
            return [item['name'] for item in form_data if item['name'] not in primary_keys]
        elif c == ConnectorEnum.MSSQL:
            mssqlc.create_connection(host=connection_data['host'], port=int(connection_data['port']),
                                     connection_user=connection_data['connection_user'],
                                     connection_password=connection_data['connection_password'],
                                     database=connection_data['database'], table=connection_data['table'])
            form_data = mssqlc.describe_table()
            primary_keys = mssqlc.get_primary_keys()
            return [item['name'] for item in form_data if item['name'] not in primary_keys]
        elif c == ConnectorEnum.JIRA:
            self.jirac.create_connection(related, plug)
            try:
                fields = self.jirac.get_meta()
                return [MapField(f, controller=ConnectorEnum.JIRA) for f in fields]
            except:
                return []
        elif c == ConnectorEnum.SugarCRM:
            ping = self.scrmc.create_connection(url=connection_data['url'],
                                                connection_user=connection_data['connection_user'],
                                                connection_password=connection_data['connection_password'])
            try:
                fields = self.scrmc.get_module_fields(plug.plug_specification.all()[0].value, get_structure=True)
                return [MapField(f, controller=ConnectorEnum.SugarCRM) for f in fields]
            except:
                return []
        elif c == ConnectorEnum.MailChimp:
            list_id = plug.plug_specification.all()[0].value
            try:
                ping = mcc.create_connection(user=connection_data['connection_user'],
                                             api_key=connection_data['api_key'])
                fields = mcc.get_list_merge_fields(list_id)
                mfl = [MapField(f, controller=ConnectorEnum.MailChimp) for f in fields]
                mfl.append(MapField({'tag': 'email_address', 'name': 'Email', 'required': True, 'type': 'email',
                                     'options': {'size': 100}}, controller=ConnectorEnum.MailChimp))
                return mfl
            except:
                return []
        elif c == ConnectorEnum.GoogleSpreadSheets:
            self.gsc.create_connection(related, plug)
            values = self.gsc.get_worksheet_first_row()
            return values
        elif c == ConnectorEnum.Slack:
            self.slack_controller.create_connection(related)
            fields = self.slack_controller.get_target_fields()
            return fields
        elif c == ConnectorEnum.Bitbucket:
            self.bitbucketc.create_connection(related, plug)
            try:
                fields = self.bitbucketc.get_meta()
                return [MapField(f, controller=ConnectorEnum.Bitbucket) for f in fields]
            except:
                return []
        elif c == ConnectorEnum.GoogleContacts:
            self.google_contacts_controller.create_connection(related, plug)
            values = self.google_contacts_controller.get_mapping_fields()
            return values
        elif c == ConnectorEnum.GetResponse:
            self.getresponsec.create_connection(related, plug)
            try:
                if plug.plug_specification.all()[0].action_specification.action.name == 'Unsubscribe':
                    fields = self.getresponsec.get_unsubscribe_target_fields()
                else:
                    fields = self.getresponsec.get_meta()
                return [MapField(f, controller=ConnectorEnum.GetResponse) for f in fields]
            except:
                return []
        elif c == ConnectorEnum.GoogleCalendar:
            self.gcc.create_connection(related, plug)
            try:
                fields = self.gcc.get_meta()
                return [MapField(f, controller=ConnectorEnum.GoogleCalendar) for f in fields]
            except:
                return []
        elif c == ConnectorEnum.Twitter:
            self.twitterc.create_connection(related, plug)
            fields = self.twitterc.get_target_fields()
            return fields
        elif c == ConnectorEnum.YouTube:
            self.youtubec.create_connection(related, plug)
            try:
                fields = self.youtubec.get_target_fields()
                return [MapField(f, controller=ConnectorEnum.YouTube) for f in fields]
            except:
                return []
        elif c == ConnectorEnum.SMS:
            self.smsc.create_connection(related, plug)
            fields = self.smsc.get_target_fields()
            return fields

        else:
            try:
                controller = controller_class(**connection_data)
                return controller.get_mapping_fields()
            except Exception as e:
                print(e)
                return []

    def get_source_data_list(self, plug, connection):
        return StoredData.objects.filter(plug=plug, connection=connection).values('name').distinct()


class GearMapGetSourceData(TemplateViewWithPost):
    pass


class GearMapSendTargetData(TemplateViewWithPost):
    pass


def gear_toggle(request, gear_id):
    if request.is_ajax() is True and request.method == 'POST':
        try:
            g = Gear.objects.get(pk=gear_id)
            if g.user == request.user:
                if g.gear_map.is_active is True:
                    g.is_active = not g.is_active
                    g.save()
                else:
                    return JsonResponse({'data': 'There\'s no active gear map.'})
            else:
                return JsonResponse({'data': "You don't have permission to toogle this gear."})
        except Gear.DoesNotExist:
            return JsonResponse({'data': 'Error invalid gear id.'})
        except GearMap.DoesNotExist:
            return JsonResponse({'data': 'There\'s no active gear map.'})
        return JsonResponse({'data': g.is_active})
    return JsonResponse({'data': 'request needs to be ajax'})


def get_authorization(request):
    credentials = client.OAuth2Credentials.from_json(request.session['google_credentials'])
    return credentials.authorize(httplib2.Http())
