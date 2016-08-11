from django.shortcuts import render
from apps.api.models import Connector


# Create your views here.

def api_prueba(request):
    connector_list = Connector.objects.all()

    contenido = "Prueba hola hola"
    ctx = {'contenido': contenido, 'connectorList': connector_list}
    return render(request, 'home/index.html', ctx)
