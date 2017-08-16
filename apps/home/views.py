from django.shortcuts import redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
import json
from apps.user.views import LoginView
from apps.gp.models import PlugActionSpecification, Webhook
from apps.gp.enum import ConnectorEnum
from urllib.parse import unquote


class DashBoardView(LoginRequiredMixin, TemplateView):
    template_name = 'home/dashboard.html'

    def get(self, *args, **kwargs):
        return super(DashBoardView, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashBoardView, self).get_context_data(**kwargs)
        context["message"] = "Hello!"
        return context


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
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)
        if connector == ConnectorEnum.Instagram:
            mode = request.GET.get('hub.mode', None)
            challenge = request.GET.get('hub.challenge', None)
            token = request.GET.get('hub.verify_token', None)
            if mode != 'subscribe' or not token or token != self.INSTAGRAM_TOKEN:
                return HttpResponse(status=200)
            return HttpResponse(challenge)
        return HttpResponse(status=403)

    def head(self, request, *args, **kwargs):
        print('head')
        response = HttpResponse(status=500)
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)
        if connector == ConnectorEnum.SurveyMonkey:
            response.status_code = 200
            return response

    def post(self, request, *args, **kwargs):
        force_update = request.POST.get('force_update', False)
        response = HttpResponse(status=500)
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)
        controller_class = ConnectorEnum.get_controller(connector)
        controller = controller_class()
        # SLACK
        response = HttpResponse(status=200)
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception as e:
            print(e)
            body = None
        if connector in [ConnectorEnum.Slack, ConnectorEnum.SurveyMonkey]:
            response = controller.do_webhook_process(body=body, post=request.POST, get=request.GET)
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
            response.status_code = 200
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
        elif connector == ConnectorEnum.Gmail:
            webhook_id = kwargs.pop('webhook_id', None)
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
        elif connector == ConnectorEnum.MercadoLibre:
            decoded = json.loads(request.body.decode("utf-8"))
            response.status_code = 200
            print(decoded)
        return response
