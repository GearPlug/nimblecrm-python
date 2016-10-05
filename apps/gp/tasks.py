from apps.gp.models import Gear, StoredData, GearMapData, PlugSpecification
from apps.gp.enum import ConnectorEnum
from apps.api.views import mysql_get_insert_values, mysql_trigger_create_row
from apps.gp.controllers import SugarCRMController
from apiconnector.celery import app


@app.task
def add2(x, y):
    return x + y


@app.task
def update_gears():
    print("Starting to update gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).select_related('gear_map')
    gear_amount = len(active_gears)
    try:
        percentil = 100 / gear_amount
        print("A total of %s gears will be updated." % len(active_gears))
    except ZeroDivisionError:
        print("There are no gears to update.")
        return

    for i, gear in enumerate(active_gears):
        update_source_plug(i, gear, percentil)
    print("Finished updating Gear's Source Plugs...")

    for i, gear in enumerate(active_gears):
        is_first = True if gear.gear_map.last_sent_stored_data_id is None else False
        update_target_plug(i, gear, percentil, is_first=is_first)
    print("Finished updating Gear's Target Plugs...")
    print("Integrity checks...")
    return True


def update_source_plug(i, gear, percentil):
    print('Updating source for gear: %s. (%s%%)' % (i + 1, (i + 1) * percentil,))
    connector = ConnectorEnum.get_connector(gear.source.connection.connector.id)
    controller_class = ConnectorEnum.get_controller(connector)
    if controller_class == SugarCRMController:
        controller = controller_class(gear.source.connection.related_connection, gear.source,
                                      gear.source.plug_specification.all()[0].value)
    else:
        controller = controller_class(gear.source.connection.related_connection, gear.source)
    controller.download_source_data()


def update_target_plug(i, gear, percentil, is_first=False):
    print('Updating target for gear: %s. (%s%%)' % (gear.id, (i + 1) * percentil,))
    kwargs = {'connection': gear.source.connection, 'plug': gear.source,}
    if gear.gear_map.last_sent_stored_data_id is not None:
        kwargs['id__gt'] = gear.gear_map.last_sent_stored_data_id
    stored_data = StoredData.objects.filter(**kwargs)
    if not stored_data:
        print("no data")
        return
    connector = ConnectorEnum.get_connector(gear.target.connection.connector.id)
    target_fields = {data.target_name: data.source_value for data in
                     GearMapData.objects.filter(gear_map=gear.gear_map)}
    source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}}
                   for item in stored_data.values_list('object_id').distinct()]
    connection = gear.target.connection
    print(connector)
    if connector == ConnectorEnum.MySQL:
        columns, insert_values = mysql_get_insert_values(source_data, target_fields, connection.related_connection)
        print(columns)
        print(insert_values)
        mysql_trigger_create_row(connection.related_connection, columns, insert_values)
    elif connector == ConnectorEnum.SugarCRM:
        controller_class = ConnectorEnum.get_controller(connector)
        controller = controller_class(gear.target.connection.related_connection, gear.target)
        entries = controller.send_stored_data(source_data, target_fields, is_first=is_first)
        print('data %s' % len(source_data))
    # gear.gear_map.last_sent_stored_data_id = stored_data.order_by('-id')[0].id
    # gear.gear_map.save()
