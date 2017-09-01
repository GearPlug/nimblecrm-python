from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View, ListView
from django.views.decorators.csrf import csrf_exempt
from allauth.account.views import LoginView
from apps.gp.models import GearGroup, Gear, PlugActionSpecification, Plug, Webhook, Connector
from apps.gp.enum import ConnectorEnum
import json


class DashBoardView(LoginRequiredMixin, TemplateView):
    template_name = 'home/dashboard.html'

    def get(self, *args, **kwargs):
        return super(DashBoardView, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashBoardView, self).get_context_data(**kwargs)
        context['gear_groups'] = GearGroup.objects.filter(user=self.request.user)[:3]
        context['used_gears'] = Gear.objects.filter(user=self.request.user)[:3]
        return context


class AppsView(LoginRequiredMixin, ListView):
    """
    Lists all connectors that can be used as the type requested.

    - Called after creating a gear.
    - Called after testing the source plug.

    """
    model = Connector
    template_name = 'home/app_list.html'
    login_url = '/account/login/'


class HomeView(LoginView):
    template_name = 'home/index.html'
    success_url = '/dashboard/'

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated():
            return redirect(self.get_success_url())
        return super(HomeView, self).get(*args, **kwargs)


class IncomingWebhook(View):
    INSTAGRAM_TOKEN = 'GearPlug2017'

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        # print('dispatch')
        return super(IncomingWebhook, self).dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        response = HttpResponse(status=400)
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)

        if connector in [ConnectorEnum.FacebookLeads]:
            controller_class = ConnectorEnum.get_controller(connector)
            controller = controller_class()
            response = controller.do_webhook_process(GET=request.GET)
        if connector == ConnectorEnum.Instagram:
            mode = request.GET.get('hub.mode', None)
            challenge = request.GET.get('hub.challenge', None)
            token = request.GET.get('hub.verify_token', None)
            if mode != 'subscribe' or not token or token != self.INSTAGRAM_TOKEN:
                response.status_code = 200
                response.content = challenge
        return response

    def head(self, request, *args, **kwargs):
        response = HttpResponse(status=400)
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)
        if connector == ConnectorEnum.SurveyMonkey:
            response.status_code = 200
            return response

    def post(self, request, *args, **kwargs):
        response = HttpResponse(status=400)
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)
        controller_class = ConnectorEnum.get_controller(connector)
        controller = controller_class()
        print(connector)
        # SLACK
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception as e:
            print(e)
            body = None
        if connector in [ConnectorEnum.Slack, ConnectorEnum.SurveyMonkey, ConnectorEnum.Gmail,
                         ConnectorEnum.FacebookLeads, ConnectorEnum.MercadoLibre]:
            response = controller.do_webhook_process(body=body, POST=request.POST)
            return response
        # ASANA
        elif connector == ConnectorEnum.Asana:
            if 'HTTP_X_HOOK_SECRET' in request.META:
                response['X-Hook-Secret'] = request.META[
                    'HTTP_X_HOOK_SECRET']
                return response
            decoded_events = json.loads(request.body.decode("utf-8"))
            events = decoded_events['events']
            controller_class = ConnectorEnum.get_controller(connector)
            for event in events:
                if event['type'] == 'task' and event['action'] == 'added':
                    project_list = PlugActionSpecification.objects.filter(
                        action_specification__action__action_type='source',
                        action_specification__action__connector__name__iexact='asana',
                        action_specification__name__iexact='project',
                        value=event['parent'])
                    for project in project_list:
                        controller = controller_class(
                            project.plug.connection.related_connection,
                            project.plug)
                        ping = controller.test_connection()
                        if ping:
                            controller.download_source_data(event=event)
            response.status_code = 200
        elif connector == ConnectorEnum.JIRA:
            data = json.loads(request.body.decode('utf-8'))
            issue = data['issue']
            project_list = PlugActionSpecification.objects.filter(
                action_specification__action__action_type='source',
                action_specification__action__connector__name__iexact="jira",
                action_specification__name__iexact='project_id',
                value=issue['fields']['project']['id'], )
            controller_class = ConnectorEnum.get_controller(connector)
            for project in project_list:
                controller = controller_class(
                    project.plug.connection.related_connection,
                    project.plug)
                ping = controller.test_connection()
                if ping:
                    controller.download_source_data(issue=issue)
        elif connector == ConnectorEnum.WunderList:
            response = HttpResponse(status=200)
            controller_class = ConnectorEnum.get_controller(connector)
            task = json.loads(request.body.decode("utf-8"))
            if 'operation' in task:
                kwargs = {'action_specification__action__action_type': 'source',
                          'action_specification__action__connector__name__iexact': 'wunderlist',
                          'action_specification__name__iexact': 'list',
                          'value': task['subject']['parents'][0]['id']}
                if task['operation'] == 'create':
                    kwargs['action_specification__action__name__iexact'] = 'new task'
                    print('se creo una tarea')
                elif task['operation'] == 'update':
                    if 'completed' in task['data'] and task['data']['completed'] == True:
                        print('se completo una tarea')
                        kwargs['action_specification__action__name__iexact'] = 'completed task'
                try:
                    specification_list = PlugActionSpecification.objects.filter(**kwargs)
                except Exception as e:
                    specification_list = []
                for s in specification_list:
                    controller = controller_class(
                        s.plug.connection.related_connection, s.plug)
                    ping = controller.test_connection()
                    if ping:
                        controller.download_source_data(task=task)
        elif connector == ConnectorEnum.GoogleCalendar:
            webhook_id = kwargs.pop('webhook_id', None)
            w = Webhook.objects.get(pk=webhook_id)
            controller_class = ConnectorEnum.get_controller(connector)
            controller = controller_class(w.plug.connection.related_connection, w.plug)
            ping = controller.test_connection()
            if ping:
                events = controller.get_events()
                controller.download_source_data(events=events)
                response.status_code = 200
        elif connector == ConnectorEnum.SurveyMonkey:
            responses = []
            data = request.body.decode('utf-8')
            data = json.loads(data)
            survey = {'id': data['object_id']}
            responses.append(survey)
            qs = PlugActionSpecification.objects.filter(
                action_specification__action__action_type='source',
                action_specification__action__connector__name__iexact="SurveyMonkey",
                value=data['resources']['survey_id']
            )
            for plug_action_specification in qs:
                controller_class = ConnectorEnum.get_controller(connector)
                controller = controller_class(plug_action_specification.plug.connection.related_connection,
                                              plug_action_specification.plug)
                ping = controller.test_connection
                if ping:
                    controller.download_source_data(responses=responses)
            response.status_code = 200
        elif connector == ConnectorEnum.Shopify:
            data = []
            fields = request.body.decode('utf-8')
            fields = json.loads(fields)
            id = fields["id"]
            data.append(id)
            webhook_id = kwargs.pop('webhook_id', None)
            w = Webhook.objects.get(pk=webhook_id)
            if w.plug.gear_source.first().is_active or not w.plug.is_tested:
                if not w.plug.is_tested:
                    w.plug.is_tested = True
                controller_class = ConnectorEnum.get_controller(connector)
                controller = controller_class(w.plug.connection.related_connection, w.plug)
                ping = controller.test_connection()
                if ping:
                    controller.download_source_data(list=data)
                    w.plug.save()
            response.status_code = 200
        elif connector == ConnectorEnum.MercadoLibre:
            decoded = json.loads(request.body.decode("utf-8"))
            response.status_code = 200
            print(decoded)
        return response
