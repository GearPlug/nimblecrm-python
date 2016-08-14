from enum import Enum
from django.apps import apps


class ConnectorEnum(Enum):
    Facebook = 1
    MySQL = 2

    def get_connector_data(connector):
        connector = ConnectorEnum.get_connector(connector)
        return ConnectorEnum.get_model(connector), ConnectorEnum.get_fields(connector)

    def get_connector(connector):
        connector = int(connector)
        for field in ConnectorEnum:
            if connector == int(field.value):
                return field

    def get_fields(connector):
        if connector == ConnectorEnum.Facebook:
            return ['name', 'id_page', 'id_form']
        elif connector == ConnectorEnum.MySQL:
            return ['name', 'host', 'port', 'database', 'connection_user', 'connection_password']

    def get_model(connector):
        if connector == ConnectorEnum.Facebook:
            return apps.get_model('gp', '%sConnection' % ConnectorEnum.Facebook.name)
        elif connector == ConnectorEnum.MySQL:
            return apps.get_model('gp', '%sConnection' % ConnectorEnum.MySQL.name)
