from django.http import JsonResponse

from apps.gp.controllers.crm import ZohoCRMController
from apps.gp.views import TemplateViewWithPost


class AJAXZohoCRMTestConnection(TemplateViewWithPost):
    template_name = 'create.html'
    zohocrmcontroller = ZohoCRMController()

    def post(self, request, *args, **kwargs):
        token = self.request.POST.get('token', ' ')
        data = self.zohocrmcontroller.create_connection(token=token)
        return JsonResponse({'data': data})
