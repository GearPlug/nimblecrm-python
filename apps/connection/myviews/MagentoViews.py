from django.http import JsonResponse

from apps.gp.controllers.ecomerce import MagentoController
from apps.gp.views import TemplateViewWithPost
from apps.gp.enum import dynamic_import


class AJAXMagentoTestConnection(TemplateViewWithPost):
    template_name = 'test.html'
    magentocontroller = MagentoController()

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        host = self.request.POST.get('host', 'host')
        port = self.request.POST.get('port', 'puerto')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = self.magentocontroller.create_connection(name=name, host=host, port=int(port), connection_user=user,
                                             connection_password=password)
        return JsonResponse({'data': ping})
