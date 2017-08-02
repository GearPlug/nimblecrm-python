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
            print(len(events))
            update_events = []
            for event in events:
                if event['type'] == 'task' and event['action'] == 'added':
                    print(event['type'], event['action'], event['parent'])
                    # print(event)
                    project_list = PlugActionSpecification.objects.filter(
                        action_specification__action__action_type='source',
                        action_specification__action__connector__name__iexact='asana',
                        action_specification__name__iexact='project',
                        value=event['parent'])
                    print('projects', project_list)
                    for project in project_list:
                        controller = controller_class(
                            project.plug.connection.related_connection,
                            project.plug)
                        ping = controller.test_connection()
                        if ping:
                            controller.download_source_data(event=event)
            #     else:
            #         print('*** Evento Creado, Ninguna Tarea hasta ahora. ***')
            # print(decoded_events)

            # controller = controller_class()
            return response
