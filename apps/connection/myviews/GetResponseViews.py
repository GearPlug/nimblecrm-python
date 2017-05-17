from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.gp.controllers.email_marketing import GetResponseController
from apps.gp.views import TemplateViewWithPost


class AJAXGetResponseTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    grc = GetResponseController()

    def post(self, request, *args, **kwargs):
        api_key = self.request.POST.get('api_key', 'clave')
        ping = self.grc.create_connection(api_key=api_key, )
        return JsonResponse({'data': ping})
