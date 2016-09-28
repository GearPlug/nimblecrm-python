from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse

from apps.connection.views import CreateConnectionView
from apps.gear.views import CreateGearView, UpdateGearView, CreateGearMapView
from apps.gp.controllers import FacebookController, MySQLController, SugarCRMController
from apps.gp.enum import ConnectorEnum
from apps.gp.models import Connector, Connection, Action, Gear, Plug
from apps.plug.views import CreatePlugView, UpdatePlugAddActionView, CreatePlugSpecificationsView

fbc = FacebookController()
mysqlc = MySQLController()
scrmc = SugarCRMController()


class CreateGearView(LoginRequiredMixin, CreateGearView):
    login_url = '/account/login/'
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


class SetGearPlugsView(LoginRequiredMixin, UpdateGearView):
    login_url = '/account/login/'
    template_name = 'gear/update.html'

    def get_success_url(self):
        self.request.session['gear_id'] = self.object.id
        if hasattr(self.object, 'source') and hasattr(self.object, 'target'):
            return reverse('wizard:create_gear_map', kwargs={'gear_id': self.object.id})
        return reverse('wizard:set_gear_plugs', kwargs={'pk': self.object.id})

    def form_valid(self, form, *args, **kwargs):
        self.request.session['source_plug_id'] = None
        self.request.session['target_plug_id'] = None
        return super(SetGearPlugsView, self).form_valid(form, *args, **kwargs)


class CreatePlugView(LoginRequiredMixin, CreatePlugView):
    login_url = '/account/login/'
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
        if self.request.session['gear_id'] is not None:
            gear = Gear.objects.get(pk=self.request.session['gear_id'])
            setattr(gear, self.kwargs['plug_type'], self.object)
            gear.save()
        self.request.session[
            'source_plug_id' if self.kwargs['plug_type'] == 'source' else 'target_plug_id'] = self.object.id
        return reverse('wizard:plug_set_action', kwargs={'pk': self.object.id, 'plug_type': self.kwargs['plug_type']})


class UpdatePlugSetActionView(LoginRequiredMixin, UpdatePlugAddActionView):
    login_url = '/account/login/'
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
            gear_id = None
        if gear_id is None:
            return reverse('wizard:create_gear')
        if self.kwargs['plug_type'] == 'source':
            c = ConnectorEnum.get_connector(self.object.connection.connector.id)
            conn = self.object.connection.related_connection
            if c == ConnectorEnum.Facebook:
                fbc.download_leads_to_stored_data(conn, self.object)
        if len(self.object.action.action_specification.all()) > 0:
            return reverse('wizard:plug_set_specifications',
                           kwargs={'plug_id': self.object.id,})
        return reverse('wizard:set_gear_plugs', kwargs={'pk': gear_id})


class CreatePlugSpecificationView(LoginRequiredMixin, CreatePlugSpecificationsView):
    login_url = '/account/login/'

    def get_success_url(self):
        try:
            gear_id = self.request.session['gear_id']
        except:
            gear_id = None
        if gear_id is None:
            return reverse('wizard:create_gear')
        c = ConnectorEnum.get_connector(self.object.plug.connection.connector.id)
        conn = self.object.plug.connection.related_connection
        if c == ConnectorEnum.Facebook:
            fbc.download_leads_to_stored_data(conn, self.object.plug)
        elif c == ConnectorEnum.MySQL:
            ping = mysqlc.create_connection(conn, self.object.plug)
            if ping:
                res = mysqlc.download_to_stored_data(conn, self.object.plug)
        elif c == ConnectorEnum.SugarCRM:
            if self.object.action_specification.action.is_source:
                ping = scrmc.create_connection(url=self.object.plug.connection.related_connection.url,
                                               connection_user=self.object.plug.connection.related_connection.connection_user,
                                               connection_password=self.object.plug.connection.related_connection.connection_password)
                data_list = scrmc.download_module_to_stored_data(conn, self.object.plug, self.object.value)
        return reverse('wizard:set_gear_plugs', kwargs={'pk': gear_id})

    def get_context_data(self, *args, **kwargs):
        context = super(CreatePlugSpecificationView, self).get_context_data(*args, **kwargs)
        plug = Plug.objects.get(pk=self.kwargs['plug_id'])
        c = ConnectorEnum.get_connector(plug.connection.connector.id)
        if c == ConnectorEnum.SugarCRM:
            ping = scrmc.create_connection(url=plug.connection.related_connection.url,
                                           connection_user=plug.connection.related_connection.connection_user,
                                           connection_password=plug.connection.related_connection.connection_password)
            modules = scrmc.get_available_modules()
        else:
            modules = []
        context['available_options'] = [m.module_key for m in modules]
        return context


class CreateConnectionView(LoginRequiredMixin, CreateConnectionView):
    login_url = '/account/login/'
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


class CreateGearMapView(LoginRequiredMixin, CreateGearMapView):
    login_url = '/account/login/'
    template_name = 'gear/map/create.html'

    def get_success_url(self, *args, **kwargs):
        return super(CreateGearMapView, self).get_success_url(*args, **kwargs)
