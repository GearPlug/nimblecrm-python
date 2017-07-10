import httplib2
from django.urls import reverse_lazy, reverse
from django.views.generic import CreateView, UpdateView, DeleteView, ListView, FormView
from django.http.response import JsonResponse
from apps.gear.apps import APP_NAME as app_name
from apps.gear.forms import MapForm
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.gp.controllers.database import MySQLController, PostgreSQLController, MSSQLController
from apps.gp.controllers.lead import GoogleFormsController, FacebookController
from apps.gp.controllers.crm import SugarCRMController, SalesforceController
from apps.gp.controllers.crm import SugarCRMController
from apps.gp.controllers.email import SMTPController
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


# mysqlc = MySQLController()
# postgresqlc = PostgreSQLController()
# mcc = MailChimpController()
# mssqlc = MSSQLController()


class ListGearView(LoginRequiredMixin, ListView):
    """
    Lists all gears related to the authenticated user.

    - Is not called in the wizard.
    """
    model = Gear
    template_name = 'wizard/gear_list.html'
    login_url = '/account/login/'

    def get_context_data(self, **kwargs):
        context = super(ListGearView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user)


class CreateGearView(LoginRequiredMixin, CreateView):
    """
    Creates an empty gear and associate it to the authenticated user.

    - Calls the connector list as a source.

    """
    model = Gear
    template_name = 'wizard/gear_create.html'
    fields = ['name', ]
    login_url = '/account/login/'
    success_url = reverse_lazy('wizard:connector_list', kwargs={'type': 'source'})

    def get(self, request, *args, **kwargs):
        request.session['gear_id'] = None
        return super(CreateGearView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        self.request.session['gear_id'] = self.object.id
        return reverse('wizard:connector_list', kwargs={'type': 'source'})

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(CreateGearView, self).form_valid(form)

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).prefetch_related()

    def get_context_data(self, **kwargs):
        context = super(CreateGearView, self).get_context_data(**kwargs)
        return context


class UpdateGearView(LoginRequiredMixin, UpdateView):
    """
    Updates the selected gear.

    - Calls the connector list as a source.

    TODO: VALIDAR QUE EL DUEÑO ES QUIEN LO EDITA.
    """
    model = Gear
    template_name = 'wizard/gear_create.html'
    fields = ['name', ]
    login_url = '/account/login/'
    success_url = reverse_lazy('wizard:connector_list', kwargs={'type': 'source'})

    def get(self, request, *args, **kwargs):
        request.session['gear_id'] = self.kwargs.get('pk', None)
        return super(UpdateGearView, self).get(request, *args, **kwargs)


class DeleteGearView(DeleteView):
    """
    Deletes the selected gear. Should not remove the gear from the database but mark it as deleted instead.

    """
    model = Gear
    template_name = '%s/delete.html' % app_name
    success_url = reverse_lazy('%s:list' % app_name)


class CreateGearMapView2(FormView, LoginRequiredMixin):
    """
    Creates a Map for the selected gear.

    """
    login_url = '/account/login/'
    template_name = 'gear/map/create.html'
    form_class = MapForm
    form_field_list = []
    source_object_list = []
    success_url = reverse_lazy('%s:list' % app_name)

    def get(self, request, *args, **kwargs):
        """
        Define las variables source_object_list y form_field_list, necesarias para el mapeo.
        """
        gear_id = kwargs.pop('gear_id', 0)
        gear = Gear.objects.filter(pk=gear_id).select_related('source', 'target').get(pk=gear_id)
        source_plug = Plug.objects.filter(pk=gear.source.id).select_related('connection__connector').get(
            pk=gear.source.id)
        target_plug = Plug.objects.filter(pk=gear.target.id).select_related('connection__connector').get(
            pk=gear.target.id)
        # Source options
        self.source_object_list = self.get_available_source_fields(source_plug)
        # Target fields
        self.form_field_list = self.get_target_field_list(target_plug)

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
        if c == ConnectorEnum.GoogleContacts:
            self.google_contacts_controller.create_connection(plug.connection.related_connection, plug)
            return ['%%%%%s%%%%' % field for field in self.google_contacts_controller.get_contact_fields()]
        return ['%%%%%s%%%%' % item['name'] for item in self.get_source_data_list(plug, plug.connection)]

    def get_target_field_list(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        related = plug.connection.related_connection
        controller = controller_class(related, plug)
        try:
            return controller.get_mapping_fields()
        except Exception as e:
            return []


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
    sfc = SalesforceController()
    smtpc = SMTPController()

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
        if c == ConnectorEnum.GoogleContacts:
            self.google_contacts_controller.create_connection(plug.connection.related_connection, plug)
            return ['%%%%%s%%%%' % field for field in self.google_contacts_controller.get_contact_fields()]
        return ['%%%%%s%%%%' % item['name'] for item in self.get_source_data_list(plug, plug.connection)]

    def get_target_field_list(self, plug):
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        try:
            controller = controller_class(plug.connection.related_connection, plug)
            return controller.get_mapping_fields()
        except Exception as e:
            raise
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
