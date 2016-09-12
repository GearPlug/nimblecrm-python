from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.gp.controllers import SugarCRMController
from apps.gp.views import TemplateViewWithPost

scrmc = SugarCRMController()


class AJAXSugarCRMTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        url = self.request.POST.get('url', 'url')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = scrmc.create_connection(url=url, connection_user=user, connection_password=password, )
        return JsonResponse({'data': ping})
