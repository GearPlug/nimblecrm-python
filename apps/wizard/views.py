from apps.gear.views import CreateGearView, UpdateGearView
from apps.plug.views import CreatePlugView, UpdatePlugAddActionView
from apps.connection.views import CreateConnectionView
from apps.gp.models import Connector, Connection, Action, Plug
from apps.gp.enum import ConnectorEnum
from apps.api.controllers import FacebookController, MySQLController
from django.http import JsonResponse, HttpResponseRedirect
from django.urls import reverse
import copy

fbc = FacebookController()
mysqlc = MySQLController()


class CreateGearView(CreateGearView):
    template_name = 'gear/create.html'

    def get(self, request, *args, **kwargs):
        self.request.session['source_plug_id'] = None
        self.request.session['target_plug_id'] = None
        self.request.session['auto_select_connection_id'] = None
        self.request.session['gear_id'] = None
        return super(CreateGearView, self).get(request, *args, **kwargs)

    def get_success_url(self):
        self.request.session['gear_id'] = self.object.id
        return reverse('wizard:set_gear_plugs', kwargs={'pk': self.object.id})


class SetGearPlugsView(UpdateGearView):
    template_name = 'gear/update.html'

    def get_success_url(self):
        self.request.session['gear_id'] = self.object.id
        return reverse('wizard:set_gear_plugs', kwargs={'pk': self.object.id})

    def form_valid(self, form, *args, **kwargs):
        self.request.session['source_plug_id'] = None
        self.request.session['target_plug_id'] = None
        return super(SetGearPlugsView, self).form_valid(form, *args, **kwargs)


class CreatePlugView(CreatePlugView):
    template_name = 'plug/wizard/create.html'
    fields = ['name', 'connection', ]

    def form_valid(self, form, *args, **kwargs):
        form.instance.user = self.request.user
        form.instance.plug_type = self.kwargs['plug_type']
        return super(CreatePlugView, self).form_valid(form)

    def get_context_data(self, *args, **kwargs):
        context = super(CreatePlugView, self).get_context_data(*args, **kwargs)
        querykw = {}
        if self.kwargs['plug_type'] == 'target':
            querykw['is_target'] = True
        elif self.kwargs['plug_type'] == 'source':
            querykw['is_source'] = True
        context['connector_list'] = Connector.objects.filter(**querykw).values('id', 'name')
        return context

    def get_success_url(self, *args, **kwargs):
        self.request.session[
            'source_plug_id' if self.kwargs['plug_type'] == 'source' else 'target_plug_id'] = self.object.id
        return reverse('wizard:plug_set_action', kwargs={'pk': self.object.id, 'plug_type': self.kwargs['plug_type']})


class UpdatePlugSetActionView(UpdatePlugAddActionView):
    fields = ['action']
    template_name = 'plug/wizard/update.html'

    def get_context_data(self, *args, **kwargs):
        context = super(UpdatePlugSetActionView, self).get_context_data(*args, **kwargs)
        querykw = {'action_type': self.kwargs['plug_type'], 'connector_id': self.object.connection.connector.id}
        context['action_list'] = Action.objects.filter(**querykw)
        return context

    def get_success_url(self):
        try:
            gear_id = self.request.session['gear_id']
        except:
            gear_id = 0
        if self.kwargs['plug_type'] == 'source':
            c = ConnectorEnum.get_connector(self.object.connection.connector.id)
            if c == ConnectorEnum.Facebook:
                fbc.download_leads_to_stored_data(self.object.connection.related_connection)
            elif c == ConnectorEnum.MySQL:
                ping = mysqlc.create_connection(self.object.connection.related_connection)
                if ping:
                    res = mysqlc.select_all()

        return reverse('wizard:set_gear_plugs', kwargs={'pk': gear_id})


class CreateConnectionView(CreateConnectionView):
    fields = []

    def form_valid(self, form, *args, **kwargs):
        if self.request.is_ajax():
            if self.kwargs['connector_id'] is not None:
                c = Connection.objects.create(user=self.request.user, connector_id=self.kwargs['connector_id'])
                form.instance.connection = c
                if ConnectorEnum.get_connector(self.kwargs['connector_id']) == ConnectorEnum.Facebook:
                    token = self.request.POST.get('token', '')
                    long_user_access_token = fbc.extend_token(token)
                    pages = fbc.get_pages(long_user_access_token)
                    page_token = None
                    for page in pages:
                        if page['id'] == form.instance.id_page:
                            page_token = page['access_token']
                            break
                    if page_token:
                        form.instance.token = page_token
            self.object = form.save()
            self.request.session['auto_select_connection_id'] = c.id
            return JsonResponse({'data': self.object.id is not None})
        return super(CreateConnectionView, self).form_valid(form, *args, *kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreateConnectionView, self).get_context_data(*args, **kwargs)
        return context
