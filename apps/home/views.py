from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from django.urls import reverse_lazy
from .forms import SubscriptionsForm
from apps.gp.models import Subscriptions, SubscriptionsList
from django.contrib.auth.models import User
from django.views.generic import TemplateView, View
from django.views.decorators.csrf import csrf_exempt
from apps.gp.models import GearGroup, Gear

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


class IncomingWebhook(View):
    INSTAGRAM_TOKEN = 'GearPlug2017'
    YOUTUBE_TOKEN = 'GearPlug2017'

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
        if connector == ConnectorEnum.YouTube:
            mode = request.GET.get('hub.mode', None)
            challenge = request.GET.get('hub.challenge', None)
            token = request.GET.get('hub.verify_token', None)
            if token and token == self.YOUTUBE_TOKEN:
                if mode == 'subscribe':
                    response.status_code = 200
                    response.content = challenge
                elif mode == 'unsubscribe':
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
            if connector == ConnectorEnum.YouTube:
                # TODO: Youtube receibe XML, por tanto no es necesario parsear el response a JSON.
                body = request.body.decode('utf-8')
            else:
                print(request.body.decode('utf-8'))
                body = json.loads(request.body.decode('utf-8'))
        except Exception as e:
            print(e)
            body = None
        response = controller.do_webhook_process(body=body, POST=request.POST, META=request.META,
                                                 webhook_id=kwargs['webhook_id'])
        return response


class HelpView(LoginRequiredMixin, TemplateView):
    template_name = 'home/help.html'


class SubscriptionsManagerView(LoginRequiredMixin, FormView):
    template_name = 'account/subscriptionsmanager.html'
    form_class = SubscriptionsForm
    success_url = reverse_lazy('home:dashboard')

    def get_form_kwargs(self, **kwargs):
        kwargs = super(SubscriptionsManagerView, self).get_form_kwargs(**kwargs)
        kwargs['initial'] = {
            'subscription_list': SubscriptionsList.objects.filter(subscription_list__user=self.request.user), }
        return kwargs

    def form_valid(self, form):
        all_subscriptions_lists = SubscriptionsList.objects.all()
        for list in all_subscriptions_lists:
            if list in form.cleaned_data['subscription_list']:
                subcription, created = Subscriptions.objects.get_or_create(user=self.request.user, list=list)
            else:
                Subscriptions.objects.filter(user=self.request.user, list=list).delete()
        return super(SubscriptionsManagerView, self).form_valid(form)


class GroupSessionStoreView(View):
    def get(self, request):
        store = request.session.get('group_store', {k['name']: {'is_active': True, 'id': k['id']} for k in
                                                    GearGroup.objects.filter(user=request.user).values('name', 'id')})
        if 'group_store' not in request.session:
            request.session['group_store'] = store
        return JsonResponse(store)

    def post(self, request):
        request.session['group_store'] = json.loads(request.body.decode('utf-8'))
        return JsonResponse(request.session.get('group_store'))
