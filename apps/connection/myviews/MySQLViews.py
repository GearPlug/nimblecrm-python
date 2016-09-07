from django.http import JsonResponse

from apps.gp.controllers import MySQLController
from apps.gp.views import TemplateViewWithPost

mysqlc = MySQLController()


class AJAXMySQLTestConnection(TemplateViewWithPost):
    template_name = 'test.html'

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        host = self.request.POST.get('host', 'host')
        port = self.request.POST.get('port', 'puerto')
        database = self.request.POST.get('database', 'database')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = mysqlc.create_connection(name=name, host=host, port=int(port), connection_user=user,
                                        connection_password=password, database=database)
        print(ping)
        return JsonResponse({'data': ping})

    def get_context_data(self, **kwargs):
        context = super(AJAXMySQLTestConnection, self).get_context_data(**kwargs)
        return context
