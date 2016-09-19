from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.gp.controllers import FacebookController
from apps.gp.views import TemplateViewWithPost

fbc = FacebookController()


# Vista base de facebook. Hace request utilizando el graph api.
class AJAXFacebookBaseView(TemplateViewWithPost):
    template_name = 'connection/facebook/ajax_facebook_select.html'
    has_objects = False

    def get_context_data(self, *args, **kwargs):
        context = super(AJAXFacebookBaseView, self).get_context_data(**kwargs)
        token = self.request.POST.get('user_access_token', '')
        url = kwargs.pop('url', '')
        object_list = fbc.send_request(url, token)
        if object_list:
            self.has_objects = True
        context['object_list'] = object_list
        return context


class AJAXFacebookGetAvailableConnectionsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'

    def get_context_data(self, *args, **kwargs):
        kwargs['url'] = 'me/accounts'
        context = super(AJAXFacebookGetAvailableConnectionsView, self).get_context_data(**kwargs)
        return context


class AJAXFacebookGetAvailableFormsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'

    def get_context_data(self, *args, **kwargs):
        connection_id = self.request.POST.get('connection_id', '')
        kwargs['url'] = '%s/leadgen_forms' % connection_id
        context = super(AJAXFacebookGetAvailableFormsView, self).get_context_data(**kwargs)
        return context


class AJAXFacebookGetAvailableLeadsView(AJAXFacebookBaseView):
    template_name = 'connection/facebook/ajax_facebook_select.html'
    get_data = False

    def get_context_data(self, *args, **kwargs):
        self.get_data = self.request.POST.get('get_data', False)
        form_id = self.request.POST.get('form_id', '')
        kwargs['url'] = '%s/leads' % form_id
        context = super(AJAXFacebookGetAvailableLeadsView, self).get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        context = self.get_context_data()
        if self.get_data:
            return super(TemplateView, self).render_to_response(context)
        return JsonResponse({'data': self.has_objects})
