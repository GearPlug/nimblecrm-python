from enum import Enum
from django.apps import apps


class ConnectorEnum(Enum):
    Facebook = 1
    MySQL = 2

    def get_connector_data(connector):
        connector = ConnectorEnum.get_connector(connector)
        return ConnectorEnum.get_model(connector), ConnectorEnum.get_fields(connector)

    def get_connector(connector_id):
        connector_id = int(connector_id)
        for field in ConnectorEnum:
            if connector_id == int(field.value):
                return field

    def get_fields(connector):
        model = apps.get_model('gp', '%sConnection' % connector.name)
        for f in model:
            print(f.name)
        return [f.name for f in model._meta.get_fields() if
                f.name != 'id' and f.name != 'connection']

    def get_model(connector):
        return apps.get_model('gp', '%sConnection' % connector.name)
