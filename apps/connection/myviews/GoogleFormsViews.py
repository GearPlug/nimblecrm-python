import httplib2
from oauth2client import client
from django.http import JsonResponse
from apps.gp.controllers import GoogleSpreadSheetsController
from apps.gp.views import TemplateViewWithPost


def get_authorization(request):
    credentials = client.OAuth2Credentials.from_json(request.session['google_credentials'])
    return credentials.authorize(httplib2.Http())


class AjaxGoogleFormsTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    mcc = GoogleSpreadSheetsController()

    def post(self, request, *args, **kwargs):
        try:
            credentials = request.session['google_credentials']
            ping = self.mcc.create_connection(credentials_json=credentials)
        except:
            ping = False
        return JsonResponse({'data': ping})
