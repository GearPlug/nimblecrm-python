from django.http import JsonResponse

from apps.gp.controllers.crm import SalesforceController
from apps.gp.views import TemplateViewWithPost


class AJAXSalesforceTestConnection(TemplateViewWithPost):
    template_name = 'test.html'
    sfc = SalesforceController()

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        token = self.request.POST.get('token', 'token')
        ping = self.sfc.create_connection(name=name, connection_user=user, connection_password=password, token=token)
        return JsonResponse({'data': ping})
