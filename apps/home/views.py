from django.shortcuts import redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse, HttpResponse
import json
from apps.user.views import LoginView
from apps.gp.models import PlugActionSpecification
from apps.gp.enum import ConnectorEnum


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
    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        # print('dispatch')
        return super(IncomingWebhook, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # print('post')
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)

        # SLACK
        if connector == ConnectorEnum.Slack:
            data = json.loads(request.body.decode('utf-8'))
            if 'challenge' in data.keys():
                return JsonResponse({'challenge': data['challenge']})
            elif 'type' in data.keys() and data['type'] == 'event_callback':
                event = data['event']
                if event['type'] == "message":
                    channel_list = PlugActionSpecification.objects.filter(
                        action_specification__action__action_type='source',
                        action_specification__action__connector__name__iexact="slack",
                        plug__gear_source__is_active=True,
                        # TODO  TEST NO FUNCIONA POR ESTO
                        value=event['channel'])
                    controller_class = ConnectorEnum.get_controller(connector)
                    for plug_action_specification in channel_list:
                        controller = controller_class(
                            plug_action_specification.plug.connection.related_connection,
                            plug_action_specification.plug)
                        controller.download_source_data(event=data)
            else:
                print("No callback event")
            return JsonResponse({'slack': True})

        # ASANA
        elif connector == ConnectorEnum.Asana:
            response = HttpResponse(status=200)
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
        # Jira
        elif connector == ConnectorEnum.JIRA:
            response = HttpResponse(status=200)
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
        # WUNDERLIST
        elif connector == ConnectorEnum.WunderList:
            response = HttpResponse(status=200)
            controller_class = ConnectorEnum.get_controller(connector)
            task = json.loads(request.body.decode("utf-8"))
            if 'operation' in task:
                id_list = task['subject']['parents'][0]['id']
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
                #
                try:
                    specification_list = PlugActionSpecification.objects.filter(
                        **kwargs)
                    print(len(specification_list))
                except Exception as e:
                    print(e)
                    specification_list = []
                for s in specification_list:
                    controller = controller_class(
                        s.plug.connection.related_connection, s.plug)
                    ping = controller.test_connection()
                    if ping:
                        controller.download_source_data(task=task)
            return response
        else:
            pass
        return response
