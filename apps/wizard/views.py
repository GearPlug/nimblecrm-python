import json
import httplib2
from django.views.generic import CreateView, UpdateView, ListView, DetailView, TemplateView
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import HttpResponse, redirect, HttpResponseRedirect, render
from django.template import loader, Template, Context
from django.contrib.auth.mixins import LoginRequiredMixin
from apps.connection.views import CreateConnectionView
from apps.gear.views import CreateGearView, UpdateGearView, CreateGearMapView
from apps.gp.controllers import FacebookController, MySQLController, SugarCRMController, MailChimpController, \
    GoogleSpreadSheetsController
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Connector, Connection, Action, Gear, Plug, ActionSpecification, PlugSpecification, StoredData
from apps.plug.views import CreatePlugView, UpdatePlugAddActionView, CreatePlugSpecificationsView
from oauth2client import client
from apiclient import discovery
import re

fbc = FacebookController()
mysqlc = MySQLController()
scrmc = SugarCRMController()
mcc = MailChimpController()
gsc = GoogleSpreadSheetsController()
postgresqlc = PostgreSQLController()


class CreateGearView(LoginRequiredMixin, CreateView):
    model = Gear
    template_name = 'wizard/gear_create.html'
    fields = ['name', ]
    login_url = '/account/login/'

    def get(self, request, *args, **kwargs):
        request.session['source_plug_id'] = None
        request.session['target_plug_id'] = None
        request.session['auto_select_connection_id'] = None
        request.session['gear_id'] = None
        return super(CreateGearView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        self.request.session['current_gear_id'] = self.object.id
        self.request.session['current_plug'] = 'source'
        return reverse('wizard:connector_list', kwargs={'type': 'source'})

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super(CreateGearView, self).form_valid(form)

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user).prefetch_related()


class ListConnectorView(LoginRequiredMixin, ListView):
    model = Connector
    template_name = 'wizard/connector_list.html'
    login_url = '/account/login/'

    def get_queryset(self):
        if self.kwargs['type'] == 'source':
            kw = {'is_source': True}
        elif self.kwargs['type'] == 'target':
            kw = {'is_target': True}
        return self.model.objects.filter(**kw)

    def get_context_data(self, **kwargs):
        context = super(ListConnectorView, self).get_context_data(**kwargs)
        context['type'] = self.kwargs['type']
        return context


class ListConnectionView(LoginRequiredMixin, ListView):
    model = Connection
    template_name = 'wizard/connection_list.html'
    login_url = '/account/login/'

    def get_queryset(self):
        return self.model.objects.filter(user=self.request.user,
                                         connector_id=self.kwargs['connector_id']).prefetch_related()

    def get_context_data(self, **kwargs):
        context = super(ListConnectionView, self).get_context_data(**kwargs)
        context['connector_id'] = self.kwargs['connector_id']
        return context

    def post(self, request, *args, **kwargs):
        self.object_list = []
        # context = self.get_context_data()
        connection_id = request.POST.get('connection', None)
        connector_type = kwargs['type']
        request.session['%s_connection_id' % connector_type] = connection_id
        return redirect(reverse('wizard:create_plug', kwargs={'plug_type': connector_type}))


class UpdateGearView(LoginRequiredMixin, UpdateView):
    model = Gear
    fields = ['name', 'source', 'target']
    template_name = 'wizard/gear_update.html'
    login_url = '/account/login/'

    def get_success_url(self):
        self.request.session['gear_id'] = self.object.id
        if hasattr(self.object, 'source') and hasattr(self.object, 'target'):
            return reverse('wizard:create_gear_map', kwargs={'gear_id': self.object.id})
        return reverse('wizard:gear_update', kwargs={'pk': self.object.id})

    def form_valid(self, form, *args, **kwargs):
        self.request.session['source_plug_id'] = None
        self.request.session['target_plug_id'] = None
        return super(UpdateGearView, self).form_valid(form, *args, **kwargs)


class CreatePlugView(LoginRequiredMixin, CreateView):
    model = Plug
    fields = ['connection', ]
    template_name = 'wizard/plug_create.html'
    success_url = ''
    login_url = '/account/login/'

    def get_context_data(self, **kwargs):
        context = super(CreatePlugView, self).get_context_data(**kwargs)
        context['plug_type'] = self.kwargs['plug_type']
        return context

    def form_valid(self, form, *args, **kwargs):
        form.instance.user = self.request.user
        n = int(Plug.objects.filter(connection__user=self.request.user).count()) + 1
        form.instance.name = "Plug # %s for user %s" % (n, self.request.user.email)
        form.instance.action_id = self.request.POST.get('action-id', None)
        self.object = form.save()
        exp = re.compile('(^specification-)(\d+)')
        specification_list = [{'name': m.group(0), 'id': m.group(2), 'value': self.request.POST.get(m.group(0), None)}
                              for s in self.request.POST.keys() for m in [exp.search(s)] if m]
        for s in specification_list:
            PlugSpecification.objects.create(plug=self.object, action_specification_id=s['id'], value=s['value'])
        # Download data
        c = ConnectorEnum.get_connector(self.object.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        controller = controller_class()
        ckwargs = {}
        cargs = []
        ping = controller.create_connection(self.object.connection.related_connection, self.object, *cargs, **ckwargs)
        print("PING: %s" % ping)
        if ping:
            data_list = controller.download_to_stored_data(self.object.connection.related_connection, self.object)
            print(data_list)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('wizard:plug_test', kwargs={'pk': self.object.id})


class ActionListView(ListView):
    model = Action
    template_name = 'wizard/action_list.html'

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return super(ActionListView, self).get(request, *args, **kwargs)
        plug_type = request.POST.get('type', None)
        kw = {'action_type': plug_type}
        if plug_type == 'source':
            if 'source_connection_id' in request.session:
                kw['connector_id'] = Connection.objects.get(pk=request.session['source_connection_id']).connector_id
        if plug_type == 'target':
            if 'target_connection_id' in request.session:
                kw['connector_id'] = Connection.objects.get(pk=request.session['target_connection_id']).connector_id
        self.object_list = self.model.objects.filter(**kw)
        a = [{'name': a.name, 'id': a.id} for a in self.object_list]
        return JsonResponse(a, safe=False)


class ActionSpecificationsView(ListView):
    model = ActionSpecification
    template_name = 'wizard/async/action_specification.html'

    def get_context_data(self, **kwargs):
        context = super(ActionSpecificationsView, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return super(ActionSpecificationsView, self).get(request, *args, **kwargs)
        action = Action.objects.get(pk=self.kwargs['pk'])
        kw = {'action_id': action.id}
        self.object_list = self.model.objects.filter(**kw)
        context = self.get_context_data()
        if action.connector.id == ConnectorEnum.MySQL.value:
            self.template_name = 'wizard/async/action_specification/mysql.html'
        elif action.connector.id == ConnectorEnum.SugarCRM.value:
            self.template_name = 'wizard/async/action_specification/sugarcrm.html'
        elif action.connector.id == ConnectorEnum.GoogleSpreadSheets.value:
            self.template_name = 'wizard/async/action_specification/google_sheets.html'
        return super(ActionSpecificationsView, self).render_to_response(context)


class GoogleDriveSheetList(TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        c = Connection.objects.get(pk=connection_id)
        gsc = GoogleSpreadSheetsController(c.related_connection)
        sheet_list = gsc.get_sheet_list()
        context['object_list'] = sheet_list
        return super(GoogleDriveSheetList, self).render_to_response(context)


class GoogleSheetsWorksheetList(TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        spreadsheet_id = request.POST.get('spreadsheet_id', None)
        c = Connection.objects.get(pk=connection_id)
        gsc = GoogleSpreadSheetsController(c.related_connection)
        worksheet_list = gsc.get_worksheet_list(spreadsheet_id)
        # El id es el mismo nombre del worksheet
        context['object_list'] = tuple({'id': ws['title'], 'name': ws['title']} for ws in worksheet_list)
        return super(GoogleSheetsWorksheetList, self).render_to_response(context)


class MySQLFieldList(TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        c = Connection.objects.get(pk=connection_id)
        mc = MySQLController(c.related_connection)
        field_list = mc.describe_table()
        print(field_list)
        # El id es el mismo nombre del module
        context['object_list'] = tuple({'id': f['name'], 'name': f['name']} for f in field_list)
        return super(MySQLFieldList, self).render_to_response(context)


class SugarCRMModuleList(TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        c = Connection.objects.get(pk=connection_id)
        scrmc = SugarCRMController(c.related_connection)
        module_list = scrmc.get_available_modules()
        # El id es el mismo nombre del module
        context['object_list'] = tuple({'id': m.module_key, 'name': m.module_key} for m in module_list)
        return super(SugarCRMModuleList, self).render_to_response(context)


class MailChimpListsList(TemplateView):
    pass


class UpdatePlugSetActionView(LoginRequiredMixin, UpdatePlugAddActionView):
    login_url = '/account/login/'
    fields = ['action']
    template_name = 'plug/wizard/update.html'

    def get_context_data(self, *args, **kwargs):
        context = super(UpdatePlugSetActionView, self).get_context_data(*args, **kwargs)
        querykw = {'action_type': self.kwargs['plug_type'], 'connector_id': self.object.connection.connector.id}
        context['action_list'] = Action.objects.filter(**querykw)
        return context

    def get_success_url(self):
        try:
            gear_id = self.request.session['gear_id']
        except:
            gear_id = None
        if gear_id is None:
            return reverse('wizard:create_gear')
        if self.kwargs['plug_type'] == 'source':
            c = ConnectorEnum.get_connector(self.object.connection.connector.id)
            conn = self.object.connection.related_connection
            if c == ConnectorEnum.Facebook:
                fbc.download_to_stored_data(conn, self.object)
        if len(self.object.action.action_specification.all()) > 0:
            return reverse('wizard:plug_set_specifications',
                           kwargs={'plug_id': self.object.id,})
        return reverse('wizard:set_gear_plugs', kwargs={'pk': gear_id})


class CreatePlugSpecificationView(LoginRequiredMixin, CreatePlugSpecificationsView):
    login_url = '/account/login/'

    def get_context_data(self, *args, **kwargs):
        context = super(CreatePlugSpecificationView, self).get_context_data(*args, **kwargs)
        plug = Plug.objects.get(pk=self.kwargs['plug_id'])
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        if c == ConnectorEnum.MySQL:
            ping = mysqlc.create_connection(host=plug.connection.related_connection.host,
                                            port=plug.connection.related_connection.port,
                                            connection_user=plug.connection.related_connection.connection_user,
                                            connection_password=plug.connection.related_connection.connection_password,
                                            database=plug.connection.related_connection.database,
                                            table=plug.connection.related_connection.table)
            options = mysqlc.get_primary_keys()
            context['available_options'] = options
        elif c == ConnectorEnum.SugarCRM:
            ping = scrmc.create_connection(url=plug.connection.related_connection.url,
                                           connection_user=plug.connection.related_connection.connection_user,
                                           connection_password=plug.connection.related_connection.connection_password)
            modules = scrmc.get_available_modules()
            context['available_options'] = [m.module_key for m in modules]
        elif c == ConnectorEnum.MailChimp:
            ping = mcc.create_connection(user=plug.connection.related_connection.connection_user,
                                         api_key=plug.connection.related_connection.api_key)
            options = mcc.get_lists()
            context['available_options'] = [(o['name'], o['id']) for o in options]
        elif c == ConnectorEnum.GoogleSpreadSheets:
            http_auth = get_authorization(plug.pk)
            drive_service = discovery.build('drive', 'v3', http_auth)
            files = drive_service.files().list().execute()
            sheet_list = []
            for f in files['files']:
                if 'mimeType' in f and f['mimeType'] == 'application/vnd.google-apps.spreadsheet':
                    sheet_list.append((f['id'], f['name']))
            context['sheets'] = sheet_list
        else:
            context['available_options'] = []
        return context

    def get_success_url(self):
        try:
            gear_id = self.request.session['gear_id']
        except:
            gear_id = None
        if gear_id is None:
            return reverse('wizard:create_gear')
        self.object = self.object_list[0]
        c = ConnectorEnum.get_connector(self.object.plug.connection.connector.id)
        conn = self.object.plug.connection.related_connection
        if c == ConnectorEnum.Facebook:
            fbc.download_to_stored_data(conn, self.object.plug)
        elif c == ConnectorEnum.MySQL:
            ping = mysqlc.create_connection(conn, self.object.plug)
            if ping:
                res = mysqlc.download_to_stored_data(conn, self.object.plug)
        elif c == ConnectorEnum.SugarCRM:
            if self.object.action_specification.action.is_source:
                ping = scrmc.create_connection(url=self.object.plug.connection.related_connection.url,
                                               connection_user=self.object.plug.connection.related_connection.connection_user,
                                               connection_password=self.object.plug.connection.related_connection.connection_password)
                data_list = scrmc.download_to_stored_data(conn, self.object.plug, self.object.value)
        elif c == ConnectorEnum.GoogleSpreadSheets:
            gsc = GoogleSpreadSheetsController()
            ping = gsc.create_connection(conn, self.object.plug)
            if ping:
                data_list = gsc.download_to_stored_data(conn, self.object.plug)
        return reverse('wizard:set_gear_plugs', kwargs={'pk': gear_id})


class CreateConnectionView(LoginRequiredMixin, CreateConnectionView):
    login_url = '/account/login/'
    fields = []

    def form_valid(self, form, *args, **kwargs):
        if self.request.is_ajax():
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
            self.object = form.save()
            self.request.session['auto_select_connection_id'] = c.id
            return JsonResponse({'data': self.object.id is not None})
        return super(CreateConnectionView, self).form_valid(form, *args, *kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateConnectionView, self).get_context_data(*args, **kwargs)
        return context


class CreateGearMapView(LoginRequiredMixin, CreateGearMapView):
    login_url = '/account/login/'
    template_name = 'gear/map/create.html'

    def get_success_url(self, *args, **kwargs):
        return super(CreateGearMapView, self).get_success_url(*args, **kwargs)


def get_authorization(plug_id):
    plug = Plug.objects.get(pk=plug_id)
    _json = json.dumps(plug.connection.related_connection.credentials_json)
    credentials = client.OAuth2Credentials.from_json(_json)
    return credentials.authorize(httplib2.Http())


def get_authorization2(google_sheets_connection):
    _json = json.dumps(google_sheets_connection.credentials_json)
    credentials = client.OAuth2Credentials.from_json(_json)
    return credentials.authorize(httplib2.Http())


def async_spreadsheet_info(request, plug_id, spreadsheet_id):
    http_auth = get_authorization(plug_id)
    sheets_service = discovery.build('sheets', 'v4', http_auth)
    result = sheets_service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    sheets = tuple(i['properties'] for i in result['sheets'])  # % sheets[0]['gridProperties']['rowCount']
    _sheets = [(i['index'], i['title']) for i in sheets]
    request.session['google_sheets'] = _sheets
    template = loader.get_template('home/_spreadsheet_sheets.html')
    context = {'sheets': _sheets}
    ctx = {'Success': True, 'sheets': template.render(context)}
    return HttpResponse(json.dumps(ctx), content_type='application/json')


def async_spreadsheet_values(request, plug_id, spreadsheet_id, worksheet_id):
    http_auth = get_authorization(plug_id)
    sheets_service = discovery.build('sheets', 'v4', http_auth)
    sheets = request.session['google_sheets']
    worksheet_name = next((s[1] for s in sheets if s[0] == int(worksheet_id)))
    res = sheets_service.spreadsheets().values().get(spreadsheetId=spreadsheet_id,
                                                     range='{0}!A1:Z100'.format(worksheet_name)).execute()
    values = res['values']
    column_count = len(values[0])
    row_count = len(values)
    template = loader.get_template('home/_spreadsheet_table.html')
    context = {'Values': values}
    data = {'ColumnCount': column_count, 'RowCount': row_count, 'Table': template.render(context)}
    ctx = {'Success': True, 'Data': data}
    return HttpResponse(json.dumps(ctx), content_type='application/json')


class TestPlugView(TemplateView):
    template_name = 'wizard/plug_test.html'

    def get_context_data(self, **kwargs):
        context = super(TestPlugView, self).get_context_data()
        p = Plug.objects.get(pk=self.kwargs.get('pk'))
        sd_sample = StoredData.objects.filter(plug=p, connection=p.connection).order_by('-id')[0]
        sd = StoredData.objects.filter(plug=p, connection=p.connection, object_id=None)
        context['object_list'] = sd
        return context

    def post(self, request, *args, **kwargs):
        # Download data
        p = Plug.objects.get(pk=self.kwargs.get('pk'))
        c = ConnectorEnum.get_connector(p.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        controller = controller_class()
        ckwargs = {}
        cargs = []
        ping = controller.create_connection(p.connection.related_connection, p, *cargs, **ckwargs)
        print("PING: %s" % ping)
        if ping:
            data_list = controller.download_to_stored_data(p.connection.related_connection, p)
            print(data_list)
        context = self.get_context_data()
        return super(TestPlugView, self).render_to_response(context)