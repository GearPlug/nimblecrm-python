from django.http import JsonResponse
from django.views.generic import TemplateView

from apps.gp.controllers import MailChimpController
from apps.gp.views import TemplateViewWithPost



class AJAXMailChimpTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    mcc = MailChimpController()

    def post(self, request, *args, **kwargs):
        user = self.request.POST.get('connection_user', 'usuario')
        api_key = self.request.POST.get('api_key', 'clave')
        ping = self.mcc.create_connection(user=user, api_key=api_key, )
        return JsonResponse({'data': ping})
