from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView, View, ListView
from django.views.decorators.csrf import csrf_exempt
from allauth.account.views import LoginView
from apps.gp.models import GearGroup, Gear, PlugActionSpecification, Plug, \
    Webhook, Connector
from apps.gp.enum import ConnectorEnum
import json
import pprint


class DashBoardView(LoginRequiredMixin, TemplateView):
    template_name = 'home/dashboard.html'

    def get(self, *args, **kwargs):
        return super(DashBoardView, self).get(*args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashBoardView, self).get_context_data(**kwargs)
        context['gear_groups'] = GearGroup.objects.filter(
            user=self.request.user)[:3]
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
    login_url = '/accounts/login/'

    def get_queryset(self):
        return self.model.objects.filter(is_active=True)


class HomeView(LoginView):
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
        # SLACK
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception as e:
            print(e)
            body = None
        if connector in [ConnectorEnum.Slack, ConnectorEnum.SurveyMonkey, ConnectorEnum.Gmail,
                         ConnectorEnum.FacebookLeads, ConnectorEnum.MercadoLibre, ConnectorEnum.JIRA,
                         ConnectorEnum.InfusionSoft, ConnectorEnum.Asana, ConnectorEnum.WunderList,
                         ConnectorEnum.GoogleCalendar, ConnectorEnum.SurveyMonkey, ConnectorEnum.Shopify,
                         ConnectorEnum.GitLab]:
            response = controller.do_webhook_process(body=body, POST=request.POST, META=request.META,
                                                     webhook_id=kwargs['webhook_id'])

            return response

        elif connector == ConnectorEnum.ActiveCampaign:
            response.status_code = 200
            data = []
            fields = dict(request.POST)
            data.append(fields)
            clean_data = {}
            for i in data:
                if type(i) == dict:
                    for k, v in i.items():
                        if type(v) == list:
                            if len(v) < 2:
                                clean_data[k] = v[0]
            clean_data = [clean_data]
            webhook_id = kwargs['webhook_id']
            w = Webhook.objects.get(pk=webhook_id)
            if w.plug.gear_source.first().is_active or not w.plug.is_tested:
                if not w.plug.is_tested:
                    w.plug.is_tested = True
                controller_class = ConnectorEnum.get_controller(connector)
                controller = controller_class(
                    connection=w.plug.connection.related_connection, plug=w.plug)
                ping = controller.test_connection()
                if ping:
                    controller.download_source_data(data=clean_data)
                    w.plug.save()
                response.status_code = 200

class HelpView(LoginRequiredMixin, TemplateView):
    template_name = 'home/help.html'


class ActivityView(LoginRequiredMixin, TemplateView):
    template_name = 'home/activity.html'


class TermsView(LoginRequiredMixin, TemplateView):
    template_name = 'home/terms.html'
