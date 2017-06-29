from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.generic import CreateView, UpdateView, ListView, View, TemplateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from apps.plug.apps import APP_NAME as app_name
from apps.gp.models import Gear, Plug, PlugActionSpecification, Action, ActionSpecification, Connection
from apps.gp.enum import ConnectorEnum
from extra_views import ModelFormSetView
import re


class CreatePlugView(LoginRequiredMixin, CreateView):
    """
        Creates a Plug, and assign it to the gear saved it the session.

        - Is called after selecting the connection to be used.
        - Calls the TestPlugView upon completion.
        - Uses ActionListView by AJAX.
        - Uses ActionSpecificationView by AJAX.


        TODO
        - Revisar flujo y funcionalidad
        """
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
            PlugActionSpecification.objects.create(plug=self.object, action_specification_id=s['id'], value=s['value'])
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
                if c == ConnectorEnum.Bitbucket or c == ConnectorEnum.JIRA or c == ConnectorEnum.SurveyMonkey or c == ConnectorEnum.GoogleCalendar or c == ConnectorEnum.Instagram or c == ConnectorEnum.YouTube or c == ConnectorEnum.Shopify:
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
    """
        Lists the Actions from a specific connector. Filters source or target actions as well.

        - Is used by the CreatePlugView in the wizard via AJAX.


        TODO
        - Revisar flujo y funcionalidad
    """
    model = Action
    template_name = 'wizard/action_list.html'

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return super(ActionListView, self).get(request, *args, **kwargs)
        plug_type = request.POST.get('type', None)
        kw = {'action_type': plug_type}
        if plug_type in ['source', 'target']:
            if '{0}_connection_id'.format(plug_type) in request.session:
                kw['connector_id'] = Connection.objects.get(
                    pk=request.session['{0}_connection_id'.format(plug_type)]).connector_id
        self.object_list = self.model.objects.filter(**kw)
        a = [{'name': a.name, 'id': a.id} for a in self.object_list]
        return JsonResponse(a, safe=False)


class ActionSpecificationsListView(LoginRequiredMixin, ListView):
    """
        Lists all the ActionSpecifications for a specific Action.


        - Is used by the CreatePlugView in the wizard via AJAX.


        TODO
        - Revisar flujo y funcionalidad
    """
    model = ActionSpecification
    template_name = 'wizard/async/action_specification.html'

    def get_context_data(self, **kwargs):
        context = super(ActionSpecificationsListView, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        if not request.is_ajax():
            return super(ActionSpecificationsListView, self).get(request, *args, **kwargs)
        action = Action.objects.get(pk=self.kwargs['pk'])
        kw = {'action_id': action.id}
        self.object_list = self.model.objects.filter(**kw)
        context = self.get_context_data()
        c = ConnectorEnum.get_connector(action.connector.id)
        self.template_name = 'wizard/async/action_specification/' + c.name.lower() + '.html'
        return super(ActionSpecificationsListView, self).render_to_response(context)


class CreatePlugSpecificationsView(ModelFormSetView):
    model = PlugActionSpecification
    template_name = '%s/specifications/create.html' % app_name
    fields = ['plug', 'action_specification', 'value']
    success_url = reverse_lazy('%s:list' % app_name)
    max_num = 10
    extra = 0

    def get(self, request, *args, **kwargs):
        plug = Plug.objects.get(pk=self.kwargs['plug_id'])
        print(self.extra)
        self.extra = plug.action.action_specification.count()
        return super(CreatePlugSpecificationsView, self).get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        plug = Plug.objects.get(pk=self.kwargs['plug_id'])
        self.extra = plug.action.action_specification.count()
        return super(CreatePlugSpecificationsView, self).post(request, *args, **kwargs)

    def form_valid(self, form, **kwargs):
        return super(CreatePlugSpecificationsView, self).form_valid(form, **kwargs)

    def form_invalid(self, form, **kwargs):
        return super(CreatePlugSpecificationsView, self).form_invalid(form, **kwargs)

    def get_queryset(self):
        return super(CreatePlugSpecificationsView, self).get_queryset().none()

    def get_context_data(self, *args, **kwargs):
        context = super(CreatePlugSpecificationsView, self).get_context_data(*args, **kwargs)
        plug = Plug.objects.filter(pk=self.kwargs['plug_id']).select_related('connection__connector').get(
            pk=self.kwargs['plug_id'])
        action_specification_list = [esp for esp in plug.action.action_specification.all()]
        # if esp not in []
        context['action_specification_list'] = action_specification_list
        context['plug_id'] = self.kwargs['plug_id']
        print("c")
        return context


class UpdatePlugSpecificationsView(UpdateView):
    model = PlugActionSpecification
    template_name = '%s/specifications/update.html' % app_name
    fields = ['value']
    success_url = reverse_lazy('%s:list' % app_name)


class ActionListView(View):
    def get(self, request, *args, **kwargs):
        actions = Action.objects.filter(connector_id=kwargs['connector_id'], action_type=kwargs['action_type'])
        return HttpResponse(actions)


class ActionSpecificationListView(View):
    def get(self, request, *args, **kwargs):
        specifications = ActionSpecification.objects.filter(action_id=kwargs['action_id'])
        return HttpResponse(specifications)


class PlugActionSpecificationOptionsView(LoginRequiredMixin, TemplateView):
    template_name = 'wizard/async/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        connection = Connection.objects.get(pk=connection_id)
        controller_class = ConnectorEnum.get_connector(connection.connector_id)
        controller = controller_class(connection.related_connection)
        ping = controller.tes
        if ping:
            # El id es el mismo nombre del module
            field_list = tuple({'id': f['name'], 'name': f['name']} for f in controller.describe_table())
        else:
            field_list = list()
        context['object_list'] = field_list
        return super(PlugActionSpecificationOptionsView, self).render_to_response(context)
