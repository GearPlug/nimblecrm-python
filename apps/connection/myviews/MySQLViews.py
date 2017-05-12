from django.http import JsonResponse

from apps.gp.controllers.database import MySQLController
from apps.gp.views import TemplateViewWithPost
from apps.gp.enum import dynamic_import


class AJAXMySQLTestConnection(TemplateViewWithPost):
    template_name = 'test.html'
    mysqlc = dynamic_import("MySQL", path="apps.gp.enum", suffix='Controller')#MySQLController()
    print(mysqlc)

    def post(self, request, *args, **kwargs):
        name = self.request.POST.get('name', 'nombre')
        host = self.request.POST.get('host', 'host')
        port = self.request.POST.get('port', 'puerto')
        database = self.request.POST.get('database', 'database')
        user = self.request.POST.get('connection_user', 'usuario')
        password = self.request.POST.get('connection_password', 'clave')
        ping = self.mysqlc.create_connection(name=name, host=host, port=int(port), connection_user=user,
                                             connection_password=password, database=database)
        return JsonResponse({'data': ping})
