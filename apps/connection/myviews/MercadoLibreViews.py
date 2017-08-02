from django.http import JsonResponse
from apps.gp.controllers.ecomerce import MercadoLibreController
from apps.gp.views import TemplateViewWithPost


class AjaxMercadoLibreTestConnection(TemplateViewWithPost):
    template_name = 'ajax_response.html'
    succes_url = ''
    tcc = MercadoLibreController()

    def post(self, request, *args, **kwargs):
        pass