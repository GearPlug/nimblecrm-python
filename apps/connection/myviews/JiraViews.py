from django.http import JsonResponse

from apps.gp.controllers import JiraController
from apps.gp.views import TemplateViewWithPost


class AJAXJiraTestConnection(TemplateViewWithPost):
    template_name = 'test.html'
    jirac = JiraController()

    def post(self, request, *args, **kwargs):
        host = self.request.POST.get('host', 'host')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = self.jirac.create_connection(host=host, connection_user=user, connection_password=password)
        return JsonResponse({'data': ping})
