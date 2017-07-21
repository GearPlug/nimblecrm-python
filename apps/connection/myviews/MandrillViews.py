from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.gp.controllers.email_marketing import MandrillController
from apps.gp.views import TemplateViewWithPost


class AJAXMandrillTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    mdc = MandrillController()

    def post(self, request, *args, **kwargs):
        api_key = self.request.POST.get('api_key', 'clave')
        ping = self.mdc.create_connection(api_key=api_key, )
        return JsonResponse({'data': ping})
