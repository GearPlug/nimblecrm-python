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
        connector_name = self.kwargs['connector'].lower()
        connector = ConnectorEnum.get_connector(name=connector_name)
        controller_class = ConnectorEnum.get_controller(connector)
        controller = controller_class()
        try:
            body = json.loads(request.body.decode('utf-8'))
        except Exception as e:
            print(e)
            body = None
        response = controller.do_webhook_process(body=body, POST=request.POST, META=request.META,
                                                 webhook_id=kwargs['webhook_id'])
        return response


class HelpView(LoginRequiredMixin, TemplateView):
    template_name = 'home/help.html'


class ActivityView(LoginRequiredMixin, TemplateView):
    template_name = 'home/activity.html'


class TermsView(LoginRequiredMixin, TemplateView):
    template_name = 'home/terms.html'
