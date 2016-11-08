from apps.gp.models import Gear, StoredData, GearMapData, PlugSpecification
from apps.gp.enum import ConnectorEnum
from apps.api.views import mysql_get_insert_values, mysql_trigger_create_row
from apps.gp.controllers import SugarCRMController, FacebookController
from apiconnector.celery import app
from django.core.cache import cache
from django.utils import timezone
from hashlib import md5

LOCK_EXPIRE = 60 * 1


@app.task
def update_gears():
    print("Starting to update gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True)
    gear_amount = len(active_gears)
    try:
        percentil = 100 / gear_amount
        print("A total of %s gears will be updated." % len(active_gears))
    except ZeroDivisionError:
        print("There are no gears to update.")
        return

    for i, gear in enumerate(active_gears):
        update_source_plug.s(i, gear.id, percentil).apply_async()
        update_target_plug.s(i, gear.id, percentil).apply_async()
    return True


@app.task
def update_source_plug(i, gear_id, percentil):
    gear = Gear.objects.get(pk=gear_id)
    # name_hexdigest = md5('update_target'.encode()).hexdigest()
    lock_id = 'lock-{0}-source'.format(gear.source.id)
    acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        print('Updating source for gear: %s.' % (gear.id))
        try:
            connector = ConnectorEnum.get_connector(gear.source.connection.connector.id)
            controller_class = ConnectorEnum.get_controller(connector)
            if controller_class == SugarCRMController:
                controller = controller_class(gear.source.connection.related_connection, gear.source,
                                              gear.source.plug_specification.all()[0].value)
            else:
                controller = controller_class(gear.source.connection.related_connection, gear.source)
            has_new_data = controller.download_source_data(from_date=gear.gear_map.last_source_update)
            gear.gear_map.last_source_update = timezone.now()
            gear.gear_map.save()
            return has_new_data is not None
        finally:
            release_lock()
    print("task locked")
    return False


@app.task
def update_target_plug(i, gear_id, percentil):
    gear = Gear.objects.get(pk=gear_id)
    is_first = True if gear.gear_map.last_sent_stored_data_id is None else False
    # name_hexdigest = md5('update_target'.encode()).hexdigest()
    lock_id = 'lock-{0}-target'.format(gear.target.id)
    acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        print('Updating target for gear: %s.' % gear.id)
        try:
            kwargs = {'connection': gear.source.connection, 'plug': gear.source,}
            if gear.gear_map.last_sent_stored_data_id is not None:
                kwargs['id__gt'] = gear.gear_map.last_sent_stored_data_id
            stored_data = StoredData.objects.filter(**kwargs)
            print(kwargs)
            print(stored_data.query)
            if not stored_data:
                return
            connector = ConnectorEnum.get_connector(gear.target.connection.connector.id)
            target_fields = {data.target_name: data.source_value for data in
                             GearMapData.objects.filter(gear_map=gear.gear_map)}
            source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}}
                           for item in stored_data.values_list('object_id').distinct()]
            connection = gear.target.connection
            controller_class = ConnectorEnum.get_controller(connector)
            if connector == ConnectorEnum.MySQL:
                controller = controller_class(gear.target.connection.related_connection, gear.target)
                columns, insert_values = mysql_get_insert_values(source_data, target_fields,
                                                                 connection.related_connection)
                mysql_trigger_create_row(connection.related_connection, columns, insert_values)
            elif connector == ConnectorEnum.SugarCRM:
                controller = controller_class(gear.target.connection.related_connection, gear.target)
                entries = controller.send_stored_data(source_data, target_fields, is_first=is_first)
                # print('data %s' % len(source_data))
            elif connector == ConnectorEnum.MailChimp:
                controller = controller_class(gear.target.connection.related_connection, gear.target)
                entries = controller.send_stored_data(source_data, target_fields, is_first=is_first)
            print("Saving to: %s" % stored_data.order_by('-id')[0].id)
            gear.gear_map.last_sent_stored_data_id = stored_data.order_by('-id')[0].id
            gear.gear_map.save()
            print("gear: %s, last result: %s" % (gear.id, gear.gear_map.last_sent_stored_data_id))
        finally:
            release_lock()
    print("task locked ")
    return False
