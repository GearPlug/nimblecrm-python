from django.shortcuts import render
from apps.api.models import Connector
from django.views.generic import TemplateView


# Create your views here.

def home(request):
	connector_list = Connector.objects.all()


	contenido = "Prueba hola hola"
	ctx = {'contenido':contenido, 'connectorList':connector_list}
	return render(request, 'home/index.html', ctx)


class Home(TemplateView):
	template_name = 'home/index.html'
