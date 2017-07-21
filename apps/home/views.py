from django.shortcuts import redirect
from django.views.generic import TemplateView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import JsonResponse
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
        return super(IncomingWebhook, self).dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        connector_name = self.kwargs.get('connector').lower()
        connector = ConnectorEnum.get_connector(name=connector_name)
        print(connector)
        if connector == ConnectorEnum.Slack:
            data = json.loads(request.body.decode('utf-8'))
            if 'challenge' in data.keys():
                return JsonResponse({'challenge': data['challenge']})
            elif 'type' in data.keys() and data['type'] == 'event_callback':
                print("Slack event: {0}".format(data['event']))
                event = data['event']
                slack_channel_list = PlugActionSpecification.objects.filter(
                    action_specification__action__action_type='source',
                    action_specification__action__connector__name__iexact="slack",
                    plug__source_gear__is_active=True)
                if event['type'] == "message" and event['channel'] in [c.value for c in slack_channel_list]:
                    for plug_action_specification in slack_channel_list:
                        self._slack_controller.create_connection(
                            plug_action_specification.plug.connection.related_connection,
                            plug_action_specification.plug)
                        self._slack_controller.download_source_data(event=data)
            else:
                print("No callback event")
            return JsonResponse({'slack': True})

