from apps.gp.views import TemplateViewWithPost
import MySQLdb
from django.http import JsonResponse
from apps.connection.apps import APP_NAME as app_name


class AJAXMySQLTestConnection(TemplateViewWithPost):
    template_name = 'test.html'

    def post(self, request, *args, **kwargs):
        connection_reached = False
        name = self.request.POST.get('name', 'nombre')
        host = self.request.POST.get('host', 'host')
        port = self.request.POST.get('port', 'puerto')
        database = self.request.POST.get('database', 'database')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        try:
            con = MySQLdb.connect(host=host, port=int(port), user=user, passwd=password, db=database)
            connection_reached = True
        except:
            print("Error reaching the database")
        return JsonResponse({'data': connection_reached})

    def get_context_data(self, **kwargs):
        context = super(AJAXMySQLTestConnection, self).get_context_data(**kwargs)
        return context

