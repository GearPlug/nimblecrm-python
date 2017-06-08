from django.http import JsonResponse

from apps.gp.controllers.im import SMSController
from apps.gp.views import TemplateViewWithPost


class AJAXSMSTestConnection(TemplateViewWithPost):
    template_name = 'test.html'
    smsc = SMSController()

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = self.smsc.create_connection(name=name, connection_user=user, connection_password=password)
        return JsonResponse({'data': ping})
