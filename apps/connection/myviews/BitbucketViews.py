from django.http import JsonResponse

from apps.gp.controllers import BitbucketController
from apps.gp.views import TemplateViewWithPost


class AJAXBitbucketTestConnection(TemplateViewWithPost):
    template_name = 'test.html'
    bitbucketc = BitbucketController()

    def post(self, request, *args, **kwargs):
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = self.bitbucketc.create_connection(connection_user=user, connection_password=password)
        return JsonResponse({'data': ping})
