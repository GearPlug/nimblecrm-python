from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.generic import CreateView, UpdateView, ListView, View, TemplateView, ListView, UpdateView
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Gear, Plug, PlugActionSpecification, Action, ActionSpecification, Connection, StoredData
import re


class CreatePlugView(LoginRequiredMixin, CreateView):
    """
        Creates a Plug, and assign it to the gear saved it the session.

        - Is called after selecting the connection to be used.
        - Calls the TestPlugView upon completion.
        - Uses ActionListView by AJAX.
        - Uses ActionSpecificationView by AJAX.
        - Resets the connection_id stored in the session by the ConnectionListView.

        TODO
        - Revisar flujo y funcionalidad
        """
    model = Plug
    fields = ['connection', ]
    template_name = 'plug/create.html'
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
        except Exception as e:
            print("There's no gear in session.")
        exp = re.compile('(^specification-)(\d+)')
        specification_list = [{'name': m.group(0), 'id': m.group(2), 'value': self.request.POST.get(m.group(0), None)}
                              for s in self.request.POST.keys() for m in [exp.search(s)] if m]
        for s in specification_list:
            PlugActionSpecification.objects.create(plug=self.object, action_specification_id=s['id'], value=s['value'])
        # Download data
        c = ConnectorEnum.get_connector(self.object.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        controller = controller_class(self.object.connection.related_connection, self.object)
        ping = controller.test_connection()
        if ping:
            if self.object.is_source:
                if c in [ConnectorEnum.Bitbucket, ConnectorEnum.JIRA, ConnectorEnum.SurveyMonkey,
                         ConnectorEnum.Instagram, ConnectorEnum.YouTube, ConnectorEnum.Shopify,
                         ConnectorEnum.GoogleCalendar, ConnectorEnum.Asana, ConnectorEnum.Salesforce,
                         ConnectorEnum.Mandrill, ConnectorEnum.FacebookLeads, ConnectorEnum.Gmail]:
                    controller.create_webhook()
                else:
                    controller.download_to_stored_data(self.object.connection.related_connection, self.object)
        self.request.session['source_connection_id'] = None
        self.request.session['target_connection_id'] = None
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('plug:test', kwargs={'pk': self.object.id})


class ActionListView(LoginRequiredMixin, ListView):
    """
        Lists the Actions from a specific connector. Filters source or target actions as well.

        - Is used by the CreatePlugView in the wizard via AJAX.
        - Uses the connection_id stored in the session by the ConnectionListView.

        TODO
        - Revisar flujo y funcionalidad
    """
    model = Action
    template_name = 'utils/select_options.html'

    def post(self, request, *args, **kwargs):
        return super(ActionListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        plug_type = self.request.POST.get('type', None)
        kw = {'action_type': plug_type}
        connection_key = '{0}_connection_id'.format(plug_type)
        if plug_type in ['source', 'target']:
            if connection_key in self.request.session:
                kw['connector_id'] = Connection.objects.get(pk=self.request.session[connection_key]).connector_id
        return self.model.objects.filter(**kw)


class ActionSpecificationsListView(LoginRequiredMixin, ListView):
    """
        Lists all the ActionSpecifications for a specific Action.


        - Is used by the CreatePlugView in the wizard via AJAX.


        TODO
        - Revisar flujo y funcionalidad
    """
    model = ActionSpecification
    template_name = 'plug/action_specifications.html'

    def get_context_data(self, **kwargs):
        context = super(ActionSpecificationsListView, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        action = Action.objects.get(pk=self.kwargs['action_id'])
        c = ConnectorEnum.get_connector(action.connector.id)
        if c in [ConnectorEnum.FacebookLeads, ConnectorEnum.GoogleSpreadSheets]:
            self.template_name = 'plug/action_specifications/' + c.name.lower() + '.html'
        return super(ActionSpecificationsListView, self).get(request, *args, **kwargs)

    def get_queryset(self):
        return self.model.objects.filter(action_id=self.kwargs['action_id'])


class PlugActionSpecificationListView(LoginRequiredMixin, TemplateView):
    """

    """
    template_name = 'utils/select_options.html'

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        connection_id = request.POST.get('connection_id', None)
        action_specification_id = request.POST.get('action_specification_id', None)
        connection = Connection.objects.get(pk=connection_id)
        connector = ConnectorEnum.get_connector(connection.connector_id)
        controller_class = ConnectorEnum.get_controller(connector)
        controller = controller_class(connection.related_connection)
        ping = controller.test_connection()
        kwargs.update(
            {key: val for key, val in request.POST.items() if key not in ['action_specification_id', 'connection_id']})
        if ping:
            field_list = controller.get_action_specification_options(action_specification_id, **kwargs)
        else:
            field_list = []
        context['object_list'] = field_list
        return super(PlugActionSpecificationListView, self).render_to_response(context)


class TestPlugView(TemplateView):
    """

    """
    template_name = 'plug/test.html'

    def get_context_data(self, **kwargs):
        context = super(TestPlugView, self).get_context_data()
        p = Plug.objects.get(pk=self.kwargs.get('pk'))
        if p.plug_type == 'source':
            try:
                sd_sample = StoredData.objects.filter(plug=p, connection=p.connection).order_by('-id').last()
                sd = StoredData.objects.filter(plug=p, connection=p.connection, object_id=sd_sample.object_id)
                context['object_list'] = sd
            except Exception:
                print("Failed. force donwload.")
                try:
                    c = ConnectorEnum.get_connector(p.connection.connector.id)
                    controller_class = ConnectorEnum.get_controller(c)
                    controller = controller_class(p.connection.related_connection, p)
                    ping = controller.test_connection()
                    if ping:
                        controller.download_to_stored_data(p.connection.related_connection, p)
                except Exception as e:
                    print("error")
        elif p.plug_type == 'target':
            c = ConnectorEnum.get_connector(p.connection.connector.id)
            controller_class = ConnectorEnum.get_controller(c)
            controller = controller_class(p.connection.related_connection, p)
            ping = controller.test_connection()
            if ping:
                target_fields = [field.name for field in controller.get_mapping_fields()]
                context['object_list'] = target_fields
        context['plug_type'] = p.plug_type
        return context

    def post(self, request, *args, **kwargs):
        # Download data
        p = Plug.objects.get(pk=self.kwargs.get('pk'))
        c = ConnectorEnum.get_connector(p.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(c)
        controller = controller_class(p.connection.related_connection, p)
        if p.plug_type == 'source':
            ping = controller.test_connection()
            print("PING: %s" % ping)
            if ping:
                data_list = controller.download_to_stored_data(p.connection.related_connection, p)
        context = self.get_context_data()
        return super(TestPlugView, self).render_to_response(context)
