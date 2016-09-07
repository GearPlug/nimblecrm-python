from apps.gp.models import Gear
from apps.gp.controllers import FacebookController, MySQLController
from apps.gp.enum import ConnectorEnum


def update_gears():
    print("Starting to update gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).select_related('gear_map')
    print("A total of %s gears will be updated." % len(active_gears))
    # print(active_gears)
    # Download source data
    for gear in active_gears:
        connector = ConnectorEnum.get_connector(gear.source.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(connector)
        controller = controller_class(gear.source.connection.related_connection, gear.source)
        print(gear.source.connection.related_connection.name)
        controller.download_source_data()
