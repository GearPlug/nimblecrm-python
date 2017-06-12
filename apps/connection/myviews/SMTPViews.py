from django.http import JsonResponse

from apps.gp.controllers.email import SMTPController
from apps.gp.views import TemplateViewWithPost


class AJAXSMTPTestConnection(TemplateViewWithPost):
    template_name = 'test.html'
    smtpc = SMTPController()

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        host = self.request.POST.get('host', 'host')
        port = self.request.POST.get('port', 'port')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = self.smtpc.create_connection(name=name, host=host, port=port, connection_user=user, connection_password=password)
        return JsonResponse({'data': ping})
