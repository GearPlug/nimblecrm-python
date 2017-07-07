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
from apps.gp.controllers.database import MySQLController, PostgreSQLController, MSSQLController
from apps.gp.controllers.lead import GoogleFormsController, FacebookController, SurveyMonkeyController
from apps.gp.controllers.crm import SugarCRMController, ZohoCRMController, SalesforceController
from apps.gp.controllers.email_marketing import MailChimpController, GetResponseController
from apps.gp.controllers.directory import GoogleContactsController
from apps.gp.controllers.ofimatic import GoogleSpreadSheetsController, GoogleCalendarController
from apps.gp.controllers.im import SlackController
from apps.gp.controllers.social import TwitterController, InstagramController, YouTubeController
from apps.gp.controllers.project_management import JiraController
from apps.gp.controllers.repository import BitbucketController
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Connector, Connection, Action, Gear, Plug, ActionSpecification, PlugSpecification, \
    StoredData, SlackConnection, GooglePushWebhook
from apps.plug.views import CreatePlugView
from oauth2client import client
from apiclient import discovery
from paypalrestsdk import Sale
from paypalrestsdk.notifications import WebhookEvent
import re
import paypalrestsdk
import xmltodict
import json
from apps.connection.myviews.SurveyMonkeyViews import AJAXGetSurveyListView

paypalrestsdk.configure({
    "mode": "sandbox",  # sandbox or live
    "client_id": "XXXXXXXXXXX",
    "client_secret": "YYYYYYYYYY"})

mcc = MailChimpController()
gsc = GoogleSpreadSheetsController()
gfc = GoogleFormsController()


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
                if c == ConnectorEnum.Bitbucket or c == ConnectorEnum.JIRA or c == ConnectorEnum.SurveyMonkey or c == ConnectorEnum.GoogleCalendar or c == ConnectorEnum.Instagram or c == ConnectorEnum.YouTube or c == ConnectorEnum.Salesforce:
                    controller.create_webhook()
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


class SalesforceSObjectList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = SalesforceController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            sobjects = tuple({'id': a, 'name': a} for a in controller.get_sobject_list())
        else:
            sobjects = list()
        context['object_list'] = sobjects
        return super(SalesforceSObjectList, self).render_to_response(context)


class SalesforceEventList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = SalesforceController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            events = tuple({'id': a, 'name': a} for a in controller.get_event_list())
        else:
            events = list()
        context['object_list'] = events
        return super(SalesforceEventList, self).render_to_response(context)


class SalesforceWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _instagram_controller = SalesforceController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SalesforceWebhookEvent, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode('utf-8'))

        import pprint
        print(request.META)
        pprint.pprint(data)
        # TODO Esperar que los webhooks puedan ser dinámicos
        # print(data)
        # if data[0]['changed_aspect'] != 'media':
        #     return JsonResponse({'hola': True})
        # media_id = data[0]['data']['media_id']
        # object_id = data[0]['object_id']
        # qs = PlugSpecification.objects.filter(
        #     action_specification__action__action_type='source',
        #     action_specification__action__connector__name__iexact="instagram",
        #     value=object_id,
        #     plug__source_gear__is_active=True)
        # for plug_specification in qs:
        #     self._instagram_controller.create_connection(plug_specification.plug.connection.related_connection,
        #                                                  plug_specification.plug)
        #     media = self._instagram_controller.get_media(media_id)
        #     self._instagram_controller.download_source_data(media=media)
        return JsonResponse({'hola': True})


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


class GoogleCalendarsList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = GoogleCalendarController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            calendar_list = controller.get_calendar_list()
        else:
            calendar_list = list()
        context['object_list'] = calendar_list
        return super(GoogleCalendarsList, self).render_to_response(context)


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


class ZohoCRMModuleList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = ZohoCRMController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            print("ping")
            modules = controller.get_modules()['_content'].decode()
            modules = json.loads(modules)['response']['result']['row']
            module_list = []
            for m in modules:
                if (m['pl'] != "Feeds" and m['pl'] != "Visits" and m['pl'] != "Social" and m['pl'] != "Documents"):
                    values = {'id': m['id'], 'name': m['pl']}
                    module_list.append(values)
        else:
            module_list = []
        module_list = tuple(module_list)
        context['object_list'] = module_list
        return super(ZohoCRMModuleList, self).render_to_response(context)


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


class GetResponseCampaignsList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = GetResponseController(connection.related_connection)
        ping = controller.create_connection()
        if ping:
            # El id es el mismo nombre del module
            lists_list = controller.get_campaigns()
        else:
            lists_list = []
        context['object_list'] = lists_list
        return super(GetResponseCampaignsList, self).render_to_response(context)


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


class SlackChannelList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'
    slack_controller = SlackController()

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        sc = SlackConnection.objects.get(connection_id=connection_id)
        self.slack_controller.create_connection(sc)
        context['object_list'] = self.slack_controller.get_channel_list()
        return super(SlackChannelList, self).render_to_response(context)


class SlackUserList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'
    _slack_controller = SlackController()

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        sc = SlackConnection.objects.get(connection_id=connection_id)
        self._slack_controller.create_connection(sc)
        context['object_list'] = self._slack_controller.get_channel_list()
        return super(SlackChannelList, self).render_to_response(context)


class SlackWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _slack_controller = SlackController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SlackWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(SlackWebhookEvent, self).get(request)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode('utf-8'))
        if 'challenge' in data.keys():
            return JsonResponse({'challenge': data['challenge']})
        elif 'type' in data.keys() and data['type'] == 'event_callback':
            event = data['event']
            slack_channel_list = PlugSpecification.objects.filter(
                action_specification__action__action_type='source',
                action_specification__action__connector__name__iexact="slack",
                plug__source_gear__is_active=True)
            if event['type'] == "message" and event['channel'] in [c.value for c in slack_channel_list]:
                for plug_specification in slack_channel_list:
                    self._slack_controller.create_connection(plug_specification.plug.connection.related_connection,
                                                             plug_specification.plug)
                    self._slack_controller.download_source_data(event=data)
        else:
            print("No callback event")
        return JsonResponse({'hola': True})


class SurveyMonkeyWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _surveymonkey_controller = SurveyMonkeyController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(SurveyMonkeyWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(SurveyMonkeyWebhookEvent, self).get(request)

    def post(self, request, *args, **kwargs):
        print("webhook")
        responses = []
        data = request.body.decode()
        data = json.loads(data)
        print(data['resources']['survey_id'])
        survey = {'id': data['object_id']}
        responses.append(survey)
        qs = PlugSpecification.objects.filter(
            action_specification__action__action_type='source',
            action_specification__action__connector__name__iexact="SurveyMonkey",
            value=data['resources']['survey_id']
        )
        for plug_specification in qs:
            print("plug")
            self._surveymonkey_controller.create_connection(plug_specification.plug.connection.related_connection,
                                                            plug_specification.plug)
            self._surveymonkey_controller.download_source_data(responses=responses)
        return JsonResponse({'hola': True})


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


class JiraProjectList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = JiraController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del module
            project_list = tuple({'id': p.id, 'name': p.name} for p in controller.get_projects())
        else:
            project_list = []
        context['object_list'] = project_list
        return super(JiraProjectList, self).render_to_response(context)


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
                elif c == ConnectorEnum.JIRA:
                    target_fields = controller.get_target_fields()
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


class InstagramAccountsList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = InstagramController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            # El id es el mismo nombre del module
            account_list = tuple({'id': a[0], 'name': a[1]} for a in controller.get_account())
        else:
            account_list = []
        context['object_list'] = account_list
        return super(InstagramAccountsList, self).render_to_response(context)


class InstagramWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _instagram_controller = InstagramController()
    TOKEN = 'GearPlug2017'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(InstagramWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        mode = request.GET.get('hub.mode', None)
        challenge = request.GET.get('hub.challenge', None)
        token = request.GET.get('hub.verify_token', None)
        if mode != 'subscribe' or not token or token != self.TOKEN:
            return JsonResponse({'Success': False})
        return HttpResponse(challenge)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode('utf-8'))
        if data[0]['changed_aspect'] != 'media':
            return JsonResponse({'hola': True})
        media_id = data[0]['data']['media_id']
        object_id = data[0]['object_id']
        qs = PlugSpecification.objects.filter(
            action_specification__action__action_type='source',
            action_specification__action__connector__name__iexact="instagram",
            value=object_id,
            plug__source_gear__is_active=True)
        for plug_specification in qs:
            self._instagram_controller.create_connection(plug_specification.plug.connection.related_connection,
                                                         plug_specification.plug)
            media = self._instagram_controller.get_media(media_id)
            self._instagram_controller.download_source_data(media=media)
        return JsonResponse({'hola': True})


class PaypalWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _bitbucket_controller = BitbucketController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(PaypalWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(PaypalWebhookEvent, self).get(request)

    def post(self, request, *args, **kwargs):
        webhook_id = '4EJ052258L4717728'
        transmission_id = request.META['HTTP_PAYPAL_TRANSMISSION_ID']
        timestamp = request.META['HTTP_PAYPAL_TRANSMISSION_TIME']
        actual_signature = request.META['HTTP_PAYPAL_TRANSMISSION_SIG']
        cert_url = request.META['HTTP_PAYPAL_CERT_URL']
        auth_algo = request.META['HTTP_PAYPAL_AUTH_ALGO']
        event_body = request.body.decode('utf-8')
        response = WebhookEvent.verify(
            transmission_id, timestamp, webhook_id, event_body, cert_url, actual_signature, auth_algo)
        print(response)
        # Devuelve True si es válido
        # if not response:
        #     return JsonResponse({'hola': True})
        webhook_event_json = json.loads(request.body.decode('utf-8'))
        webhook_event = WebhookEvent(webhook_event_json)
        event_resource = webhook_event.get_resource()
        print(event_resource, type(event_resource))

        print(event_resource.parent_payment)

        # payment = paypalrestsdk.Payment.find(event_resource.parent_payment)
        # print(payment)

        payment_history = paypalrestsdk.Payment.all({"count": 100})
        print(payment_history.payments)

        sale = Sale.find(event_resource.parent_payment)
        print(sale)
        return JsonResponse({'hola': True})


class YouTubeWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _youtube_controller = YouTubeController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(YouTubeWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        mode = request.GET.get('hub.mode', None)
        challenge = request.GET.get('hub.challenge', None)
        lease = request.GET.get('hub.lease_seconds', None)
        if mode != 'subscribe':
            return JsonResponse({'Success': False})
        return HttpResponse(challenge)

    def post(self, request, *args, **kwargs):
        data = request.body.decode('utf-8')
        root = xmltodict.parse(data)
        entry = root['feed']['entry']
        channel_id = entry['yt:channelId']
        video_id = entry['yt:videoId']
        qs = PlugSpecification.objects.filter(
            action_specification__action__action_type='source',
            action_specification__action__connector__name__iexact="youtube",
            value=channel_id,
            plug__source_gear__is_active=True)

        for plug_specification in qs:
            self._youtube_controller.create_connection(plug_specification.plug.connection.related_connection,
                                                       plug_specification.plug)
            video = self._youtube_controller.get_video(video_id)
            self._youtube_controller.download_source_data(video=video)
        return JsonResponse({'hola': True})


class YouTubeChannelsList(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller = YouTubeController()
        ping = controller.create_connection(connection.related_connection)
        if ping:
            channel_list = controller.get_channel_list()
        else:
            channel_list = list()
        context['object_list'] = channel_list
        return super(YouTubeChannelsList, self).render_to_response(context)


class JiraWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _jira_controller = JiraController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(JiraWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(JiraWebhookEvent, self).get(request)

    def post(self, request, *args, **kwargs):
        data = json.loads(request.body.decode('utf-8'))
        issue = data['issue']
        qs = PlugSpecification.objects.filter(
            action_specification__action__action_type='source',
            action_specification__action__connector__name__iexact="jira",
            value=issue['fields']['project']['id'],
            plug__source_gear__is_active=True)
        for plug_specification in qs:
            self._jira_controller.create_connection(plug_specification.plug.connection.related_connection,
                                                    plug_specification.plug)
            self._jira_controller.download_source_data(issue=issue)
        return JsonResponse({'hola': True})


class GoogleCalendarWebhookEvent(TemplateView):
    template_name = 'wizard/async/select_options.html'
    _googlecalendar_controller = GoogleCalendarController()

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        return super(GoogleCalendarWebhookEvent, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return super(GoogleCalendarWebhookEvent, self).get(request)

    def post(self, request, *args, **kwargs):
        resource_state = request.META.get('HTTP_X_GOOG_RESOURCE_STATE', None)
        resource_uri = request.META.get('HTTP_X_GOOG_RESOURCE_URI', None)
        channel_id = request.META.get('HTTP_X_GOOG_CHANNEL_ID', None)
        resource_id = request.META.get('HTTP_X_GOOG_RESOURCE_ID', None)
        channel_expiration = request.META.get('HTTP_X_GOOG_CHANNEL_EXPIRATION', None)
        message_number = request.META.get('HTTP_X_GOOG_MESSAGE_NUMBER', None)

        if resource_state == 'sync':
            return JsonResponse({'hola': True})

        try:
            google_push_webhook = GooglePushWebhook.objects.get(channel_id=channel_id)
        except GooglePushWebhook.DoesNotExist:
            return JsonResponse({'hola': True})

        qs = PlugSpecification.objects.filter(
            action_specification__action__action_type='source',
            action_specification__action__connector__name__iexact="googlecalendar",
            plug__connection=google_push_webhook.connection,
            plug__source_gear__is_active=True)

        for plug_specification in qs:
            self._googlecalendar_controller.create_connection(plug_specification.plug.connection.related_connection,
                                                              plug_specification.plug)
            events = self._googlecalendar_controller.get_events()
            self._googlecalendar_controller.download_source_data(events=events)

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


# def prueba1(request):
#     ctx = {}
#     return render()

class Prueba1(CreateView):
    model = Connector
    success_url = ''
    template_name = 'index.html'

    def post(self, request, *args, **kwargs):
        pass

    def get(self, request, *args, **kwargs):
        pass

    def form_valid(self, form):
        pass

    def form_invalid(self, form):
        pass
