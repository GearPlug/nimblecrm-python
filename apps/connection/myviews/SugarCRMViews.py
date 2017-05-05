from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.gp.controllers.crm import SugarCRMController
from apps.gp.views import TemplateViewWithPost


class AJAXSugarCRMTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    scrmc = SugarCRMController()

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        url = self.request.POST.get('url', 'url')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = self.scrmc.create_connection(url=url, connection_user=user, connection_password=password, )
        return JsonResponse({'data': ping})
