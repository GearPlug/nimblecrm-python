from apps.gp.models import Gear, StoredData, GearMapData, PlugSpecification
from apps.gp.enum import ConnectorEnum
from apps.api.views import mysql_get_insert_values, mysql_trigger_create_row
from apps.gp.controllers import SugarCRMController


def update_gears():
    print("Starting to update gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).select_related('gear_map')
    gear_amount = len(active_gears)
    print("A total of %s gears will be updated." % len(active_gears))
    # print(active_gears)
    # Download source data
    percentil = 100 / gear_amount
    for i, gear in enumerate(active_gears):
        print('Updating source for gear: %s. (%s%%)' % (i + 1, (i + 1) * percentil,))
        connector = ConnectorEnum.get_connector(gear.source.connection.connector.id)
        controller_class = ConnectorEnum.get_controller(connector)
        if controller_class == SugarCRMController:
            controller = controller_class(gear.source.connection.related_connection, gear.source,
                                          gear.source.plug_specification.all()[0].value)
        else:
            controller = controller_class(gear.source.connection.related_connection, gear.source)

        controller.download_source_data()
    print("Finished updating Gear's Source Plugs...")

    for i, gear in enumerate(active_gears):
        print('Updating target for gear: %s. (%s%%)' % (i + 1, (i + 1) * percentil,))
        kwargs = {'connection': gear.source.connection, 'plug': gear.source,}
        if gear.gear_map.last_sent_stored_data_id is not None:
            kwargs['id__gt'] = gear.gear_map.last_sent_stored_data_id
        stored_data = StoredData.objects.filter(**kwargs)
        if not stored_data:
            continue
        connector = ConnectorEnum.get_connector(gear.target.connection.connector.id)
        target_fields = {data.target_name: data.source_value for data in
                         GearMapData.objects.filter(gear_map=gear.gear_map)}
        source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}}
                       for item in stored_data.values_list('object_id').distinct()]
        connection = gear.target.connection
        if connector == ConnectorEnum.MySQL:
            columns, insert_values = mysql_get_insert_values(source_data, target_fields, connection.related_connection)
            mysql_trigger_create_row(connection.related_connection, columns, insert_values)
        for item in stored_data:
            print(item.id)
        print(stored_data.order_by('-id')[0].id)
        gear.gear_map.last_sent_stored_data_id = stored_data.order_by('-id')[0].id
        gear.gear_map.save()
    print("Finished updating Gear's Target Plugs...")
    print("Integrity checks...")
