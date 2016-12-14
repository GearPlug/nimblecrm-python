import httplib2
from oauth2client import client
from django.http import JsonResponse
from apps.gp.controllers import GoogleSpreadSheetsController
from apps.gp.views import TemplateViewWithPost


def get_authorization(request):
    credentials = client.OAuth2Credentials.from_json(request.session['google_credentials'])
    return credentials.authorize(httplib2.Http())


class AjaxGoogleSpreadSheetTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    mcc = GoogleSpreadSheetsController()

    def post(self, request, *args, **kwargs):
        print(request.session)
        print(request.session.items())
        print(request.user)

        credentials = request.session['google_credentials']
        ping = self.mcc.create_connection(credentials_json=credentials)
        return JsonResponse({'data': ping})
