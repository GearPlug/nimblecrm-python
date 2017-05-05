from django.http import JsonResponse
from apps.gp.controllers.social import TwitterController
from apps.gp.views import TemplateViewWithPost


class AjaxTwitterTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    tcc = TwitterController()

    def post(self, request, *args, **kwargs):
        try:
            credentials = request.session['google_credentials']
            ping = self.tcc.create_connection(credentials_json=credentials)
        except:
            ping = False
        return JsonResponse({'data': ping})
