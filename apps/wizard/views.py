import json
import httplib2
from django.views.generic import CreateView, UpdateView, ListView, TemplateView
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import HttpResponse, redirect, HttpResponseRedirect
from django.template import loader
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.decorators import method_decorator
from apps.connection.views import CreateConnectionView
from apps.gear.views import CreateGearView, UpdateGearView, CreateGearMapView
from apps.gp.controllers import FacebookController, MySQLController, SugarCRMController, MailChimpController, \
    GoogleSpreadSheetsController, PostgreSQLController, MSSQLController, BitbucketController
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Connector, Connection, Action, Gear, Plug, ActionSpecification, PlugSpecification, StoredData
from apps.plug.views import CreatePlugView
from oauth2client import client
from apiclient import discovery
import re

mcc = MailChimpController()
gsc = GoogleSpreadSheetsController()


class ListGearView(LoginRequiredMixin, ListView):
    model = Gear
    template_name = 'wizard/gear_list.html'
    login_url = '/account/login/'

    def get_context_data(self, **kwargs):
        context = super(ListGearView, self).get_context_data(**kwargs)
        return context

    def get_queryset(self):
        queryset = self.model._default_manager.all()
        return queryset.filter(user=self.request.user)


class CreateGearView(LoginRequiredMixin, CreateView):
    model = Gear
    template_name = 'wizard/gear_create.html'
    fields = ['name', ]
    login_url = '/account/login/'

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


class UpdateGearView(LoginRequiredMixin, UpdateView):
    model = Gear
    template_name = 'wizard/gear_create.html'
    fields = ['name', ]
    login_url = '/account/login/'
    success_url = reverse_lazy('wizard:connector_list', kwargs={'type': 'source'})

    def get(self, request, *args, **kwargs):
        request.session['gear_id'] = self.kwargs.get('pk', None)
        return super(UpdateGearView, self).get(request, *args, **kwargs)


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
        return redirect(reverse('wizard:plug_create', kwargs={'plug_type': connector_type}))


class CreateConnectionView(LoginRequiredMixin, CreateConnectionView):
    login_url = '/account/login/'
    fields = []

    def form_valid(self, form, *args, **kwargs):
        if self.request.is_ajax():
            if self.kwargs['connector_id'] is not None:
                c = Connection.objects.create(user=self.request.user, connector_id=self.kwargs['connector_id'])
                form.instance.connection = c
                if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Facebook:
                    fbc = FacebookController()
                    token = self.request.POST.get('token', '')
                    long_user_access_token = fbc.extend_token(token)
                    form.instance.token = long_user_access_token
            self.object = form.save()
            self.request.session['auto_select_connection_id'] = c.id
            return JsonResponse({'data': self.object.id is not None})
        return super(CreateConnectionView, self).form_valid(form, *args, *kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateConnectionView, self).get_context_data(*args, **kwargs)
        return context


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
        form.instance.plug_type = self.kwargs['plug_type']
        self.object = form.save()
        try:
            g = Gear.objects.get(pk=self.request.session['gear_id'])
            if self.object.plug_type == 'source':
                g.source = self.object
            elif self.object.plug_type == 'target':
                g.target = self.object
            g.save()
        except:
            print("There's no gear in session.")
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
            if self.object.is_source:
                controller.download_to_stored_data(self.object.connection.related_connection, self.object)
            elif self.object.is_target:
                if c == ConnectorEnum.MailChimp:
                    controller.get_target_fields(list_id=specification_list[0]['value'])
        self.request.session['source_connection_id'] = None
        self.request.session['target_connection_id'] = None
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('wizard:plug_test', kwargs={'pk': self.object.id})


class ActionListView(LoginRequiredMixin, ListView):
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


class ActionSpecificationsView(LoginRequiredMixin, ListView):
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
        c = ConnectorEnum.get_connector(action.connector.id)
        self.template_name = 'wizard/async/action_specification/' + c.name.lower() + '.html'
        return super(ActionSpecificationsView, self).render_to_response(context)


class GoogleDriveSheetList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = GoogleSpreadSheetsController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            sheet_list = controller.get_sheet_list()
        else:
            sheet_list = list()
        context['object_list'] = sheet_list
        return super(GoogleDriveSheetList, self).render_to_response(context)


class GoogleSheetsWorksheetList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        spreadsheet_id = request.POST.get('spreadsheet_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = GoogleSpreadSheetsController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del worksheet
            worksheet_list = tuple(
                {'id': ws['title'], 'name': ws['title']} for ws in controller.get_worksheet_list(spreadsheet_id))
        else:
            worksheet_list = list()
        context['object_list'] = worksheet_list
        return super(GoogleSheetsWorksheetList, self).render_to_response(context)


class MySQLFieldList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = MySQLController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del module
            field_list = tuple({'id': f['name'], 'name': f['name']} for f in controller.describe_table())
        else:
            field_list = list()
        context['object_list'] = field_list
        return super(MySQLFieldList, self).render_to_response(context)


class PostgreSQLFieldList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = PostgreSQLController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del module
            field_list = tuple({'id': f['name'], 'name': f['name']} for f in controller.describe_table())
        else:
            field_list = []
        context['object_list'] = field_list
        return super(PostgreSQLFieldList, self).render_to_response(context)


class MSSQLFieldList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = MSSQLController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del module
            field_list = tuple({'id': f['name'], 'name': f['name']} for f in controller.describe_table())
        else:
            field_list = []
        context['object_list'] = field_list
        return super(MSSQLFieldList, self).render_to_response(context)


class SugarCRMModuleList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = SugarCRMController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del module
            module_list = tuple({'id': m.module_key, 'name': m.module_key} for m in controller.get_available_modules())
        else:
            module_list = []
        context['object_list'] = module_list
        return super(SugarCRMModuleList, self).render_to_response(context)


class MailChimpListsList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = MailChimpController(connection.related_connection)
        ping = controller.create_connection()
        if ping:
            # El id es el mismo nombre del module
            lists_list = controller.get_lists()
        else:
            lists_list = []
        context['object_list'] = lists_list
        return super(MailChimpListsList, self).render_to_response(context)


class FacebookPageList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = FacebookController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            token = connection.related_connection.token
            pages = controller.get_pages(token)
            page_list = tuple({'id': p['id'], 'name': p['name']} for p in pages)
        else:
            page_list = []
        context['object_list'] = page_list
        return super(FacebookPageList, self).render_to_response(context)


class FacebookFormList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        page_id = request.POST.get('page_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = FacebookController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            token = connection.related_connection.token
            forms = controller.get_forms(token, page_id)
            form_list = tuple({'id': p['id'], 'name': p['name']} for p in forms)
        else:
            form_list = []
        context['object_list'] = form_list
        return super(FacebookFormList, self).render_to_response(context)


class BitbucketProjectList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = BitbucketController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del module
            project_list = tuple({'id': p['uuid'], 'name': p['name']} for p in controller.get_repositories())
        else:
            project_list = []
        context['object_list'] = project_list
        return super(BitbucketProjectList, self).render_to_response(context)


class TestPlugView(TemplateView):
    template_name = 'wizard/plug_test.html'

    def get_context_data(self, **kwargs):
        context = super(TestPlugView, self).get_context_data()
        p = Plug.objects.get(pk=self.kwargs.get('pk'))
        if p.plug_type == 'source':
            try:
                sd_sample = StoredData.objects.filter(plug=p, connection=p.connection).order_by('-id')[0]
                sd = StoredData.objects.filter(plug=p, connection=p.connection, object_id=sd_sample.object_id)
                context['object_list'] = sd
            except IndexError:
                pass
        elif p.plug_type == 'target':
            c = ConnectorEnum.get_connector(p.connection.connector.id)
            controller_class = ConnectorEnum.get_controller(c)
            controller = controller_class()
            ckwargs = {}
            cargs = []
            ping = controller.create_connection(p.connection.related_connection, p, *cargs, **ckwargs)
            if ping:
                if c == ConnectorEnum.MailChimp:
                    target_fields = controller.get_target_fields(list_id=p.plug_specification.all()[0].value)
                elif c == ConnectorEnum.SugarCRM:
                    target_fields = controller.get_target_fields(p.plug_specification.all()[0].value)
                else:
                    target_fields = controller.get_target_fields()
                context['object_list'] = target_fields
        context['plug_type'] = p.plug_type
        return context

    def post(self, request, *args, **kwargs):
        # Download data
        p = Plug.objects.get(pk=self.kwargs.get('pk'))
        c = ConnectorEnum.get_connector(p.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        controller = controller_class()
        ckwargs = {}
        cargs = []
        if p.plug_type == 'source':
            ping = controller.create_connection(p.connection.related_connection, p, *cargs, **ckwargs)
            print("PING: %s" % ping)
            if ping:
                data_list = controller.download_to_stored_data(p.connection.related_connection, p)
                print(data_list)
        context = self.get_context_data()
        return super(TestPlugView, self).render_to_response(context)


class CreateGearMapView(LoginRequiredMixin, CreateGearMapView):
    login_url = '/account/login/'
    template_name = 'gear/map/create.html'

    def get_success_url(self, *args, **kwargs):
        return super(CreateGearMapView, self).get_success_url(*args, **kwargs)


class BitbucketWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _bitbucket_controller = BitbucketController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(BitbucketWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(BitbucketWebhookEvent, self).get(request)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode('utf-8'))
        issue = data['issue']
        qs = PlugSpecification.objects.filter(
            action_specification__action__action_type='source',
            action_specification__action__connector__name__iexact="bitbucket",
            plug__source_gear__is_active=True)
        for plug_specification in qs:
            self._bitbucket_controller.create_connection(plug_specification.plug.connection.related_connection,
                                                         plug_specification.plug)
            self._bitbucket_controller.download_source_data(issue=issue)
        return JsonResponse({'hola': True})


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
