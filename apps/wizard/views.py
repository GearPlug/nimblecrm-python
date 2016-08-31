from apps.gear.views import CreateGearView, UpdateGearView
from apps.plug.views import CreatePlugView
from apps.connection.views import CreateConnectionView
from apps.gp.models import Connector, Connection
from apps.gp.enum import ConnectorEnum
from apps.api.controllers import FacebookController
from django.http import JsonResponse
from django.urls import reverse

fbc = FacebookController()


class CreateGearView(CreateGearView):
    template_name = 'gear/create.html'

    def get_success_url(self):
        return reverse('wizard:set_gear_plugs', kwargs={'pk': self.object.id})


class SetGearPlugsView(UpdateGearView):
    template_name = 'gear/update.html'

    def get_success_url(self):
        return reverse('wizard:set_gear_plugs', kwargs={'pk': self.object.id})


class CreatePlugView(CreatePlugView):
    template_name = 'plug/wizard/create.html'
    fields = ['name', 'connection', 'action']

    def get(self, request, *args, **kwargs):
        return super(CreatePlugView, self).get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        context = super(CreatePlugView, self).get_context_data(*args, **kwargs)
        querykw = {}
        if self.kwargs['plug_type'] == 'target':
            querykw['is_target'] = True
        elif self.kwargs['plug_type'] == 'sourcer':
            querykw['is_source'] = True
        context['connector_list'] = Connector.objects.filter(**querykw).values('id', 'name')
        return context


class CreateConnectionView(CreateConnectionView):
    fields = []

    # def post(self):
    #
    def form_valid(self, form, *args, **kwargs):
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
                fbc.download_leads_to_stored_data(form.instance)
        if self.request.is_ajax():
            self.object = form.save()
            self.request.session['auto_select_connection_id'] = c.id
            return JsonResponse({'data': self.object.id is not None})
        return super(CreateConnectionView, self).form_valid(form, *args, *kwargs)
