from apps.gp.models import Gear, StoredData, GearMapData
from apps.gp.enum import ConnectorEnum
from apps.gp.controllers import SugarCRMController
from apiconnector.celery import app
from django.core.cache import cache
from django.utils import timezone

LOCK_EXPIRE = 60 * 1


@app.task
def update_gears():
    print("Starting to update gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).values('id')
    gear_amount = len(active_gears)
    try:
        print("A total of %s gears will be updated." % len(active_gears))
    except ZeroDivisionError:
        print("There are no gears to update.")
        return

    for gear in active_gears:
        update_gear.s(gear['id']).apply_async()
    return True


@app.task
def update_gear(gear_id):
    gear = Gear.objects.get(pk=gear_id)
    is_first = True if gear.gear_map.last_sent_stored_data_id is None else False
    lock_id = 'lock-{0}-gear'.format(gear.target.id)
    acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        print('Updating gear: %s.' % gear.id)
        try:
            # SOURCE
            source_connector = ConnectorEnum.get_connector(gear.source.connection.connector.id)
            controller_class = ConnectorEnum.get_controller(source_connector)
            if controller_class == SugarCRMController:
                controller = controller_class(gear.source.connection.related_connection, gear.source,
                                              gear.source.plug_specification.all()[0].value)
            else:
                controller = controller_class(gear.source.connection.related_connection, gear.source)
            has_new_data = controller.download_source_data(from_date=gear.gear_map.last_source_update)

            # TARGET
            target_connector = ConnectorEnum.get_connector(gear.target.connection.connector.id)
            controller_class = ConnectorEnum.get_controller(target_connector)
            kwargs = {'connection': gear.source.connection, 'plug': gear.source,}
            if gear.gear_map.last_sent_stored_data_id is not None:
                kwargs['id__gt'] = gear.gear_map.last_sent_stored_data_id
            stored_data = StoredData.objects.filter(**kwargs)
            if not stored_data:
                return False
            target_fields = {data.target_name: data.source_value for data in
                             GearMapData.objects.filter(gear_map=gear.gear_map)}
            source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}}
                           for item in stored_data.values_list('object_id').distinct()]
            if target_connector == ConnectorEnum.MySQL:
                controller = controller_class(gear.target.connection.related_connection, gear.target)
                controller.send_stored_data(source_data, target_fields)
            elif target_connector == ConnectorEnum.SugarCRM:
                controller = controller_class(gear.target.connection.related_connection, gear.target)
                entries = controller.send_stored_data(source_data, target_fields, is_first=is_first)
            elif target_connector == ConnectorEnum.MailChimp:
                controller = controller_class(gear.target.connection.related_connection, gear.target)
                entries = controller.send_stored_data(source_data, target_fields, is_first=is_first)
            elif target_connector == ConnectorEnum.GoogleSpreadSheets:
                controller = controller_class(gear.target.connection.related_connection, gear.target)
                controller.send_stored_data(source_data, target_fields, is_first=is_first)
            gear.gear_map.last_source_update = timezone.now()
            gear.gear_map.last_sent_stored_data_id = stored_data.order_by('-id')[0].id
            gear.gear_map.save()
        except Exception as e:
            raise
            print("Exception in task %s" % gear_id)
            pass
        finally:
            release_lock()
        return True
    return False
