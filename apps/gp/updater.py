from apps.gp.models import Gear, StoredData, GearMapData, Connection
from apps.gp.enum import ConnectorEnum
from apps.api.views import mysql_get_insert_values, mysql_trigger_create_row


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
        controller.download_source_data()

    print("Finished updating Gear's Source Plugs.")

    for gear in active_gears:
        connector = ConnectorEnum.get_connector(gear.source.connection.connector.id)
        stored_data = StoredData.objects.filter(connection=gear.source.connection)
        target_fields = {data.target_name: data.source_value for data in
                         GearMapData.objects.filter(gear_map=gear.gear_map)}
        source_data = [
            {'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}}
            for item in stored_data.values_list('object_id').distinct()]
        connection = gear.target.connection
        if connector == ConnectorEnum.MySQL:
            columns, insert_values = mysql_get_insert_values(source_data, target_fields, connection.related_connection)
            mysql_trigger_create_row(connection.related_connection, columns, insert_values)
