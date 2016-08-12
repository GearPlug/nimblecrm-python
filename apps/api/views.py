from django.shortcuts import render



# Create your views here.

def api_prueba(request):
    connector_list = []
    contenido = "Prueba hola hola"
    ctx = {'contenido': contenido, 'connectorList': connector_list}
    return render(request, 'home/index.html', ctx)
