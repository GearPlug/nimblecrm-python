from apps.gp.models import Gear, StoredData, GearMapData, Plug
from apps.gp.enum import ConnectorEnum
from apps.gp.controllers.crm import SugarCRMController
from apiconnector.celery import app
from django.core.cache import cache
from django.utils import timezone
from collections import OrderedDict

LOCK_EXPIRE = 60 * 1


# @app.task(queue="beat")
@app.task
def update_all_gears():
    print("Starting to update all gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True)
    gear_amount = active_gears.count()
    # active_gears_ids = active_gears.values('id')
    print("A total of %s gears will be updated." % gear_amount)
    for gear in active_gears:
        connector = ConnectorEnum.get_connector(gear.source.connection.connector_id)
        print("Connector: {0}".format(connector))
        # update_plug.s(gear.source.id, gear.id).apply_async(queue="source_{0}".format(connector.name.lower()))
        update_plug.s(gear.source.id, gear.id).apply_async()
        print("Asignado el plug {0} a update de source.".format(gear.source))


# @app.task(queue="connector")
@app.task
def update_plug(plug_id, gear_id, **kwargs):
    plug = Plug.objects.get(pk=plug_id)
    lock_id = 'lock-{0}-gear'.format(plug.id)
    acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        try:
            print("Updating Gear: {0} as {1}".format(gear_id, plug.plug_type))
            gear = Gear.objects.get(pk=gear_id)
            source_connector = ConnectorEnum.get_connector(plug.connection.connector.id)
            controller_class = ConnectorEnum.get_controller(source_connector)
            if controller_class == SugarCRMController:
                controller = controller_class(plug.connection.related_connection, plug,
                                              plug.plug_action_specification.all()[0].value)
            else:
                controller = controller_class(plug.connection.related_connection, plug)
            ping = controller.test_connection()
            if ping is not True:
                print("Error en la connection.")
                return
            if plug.plug_type.lower() == 'source':
                has_new_data = controller.download_source_data(from_date=gear.gear_map.last_source_update)
                if gear.gear_map.last_sent_stored_data_id is None:
                    kwargs['force_update'] = True
                if has_new_data or 'force_update' in kwargs and kwargs['force_update'] == True:
                    # connector = ConnectorEnum.get_connector(gear.target.connection.connector_id)
                    # update_plug.s(gear.target.id, gear_id).apply_async(
                    #     queue="source_{0}".format(connector.name.lower()))
                    update_plug.s(gear.target.id, gear_id).apply_async()
            elif plug.plug_type.lower() == 'target':
                kwargs = {'connection': gear.source.connection, 'plug': gear.source, }
                if gear.gear_map.last_sent_stored_data_id is not None:
                    kwargs['id__gt'] = gear.gear_map.last_sent_stored_data_id
                stored_data = StoredData.objects.filter(**kwargs)
                if stored_data:
                    target_fields = OrderedDict((data.target_name, data.source_value) for data in
                                                GearMapData.objects.filter(gear_map=gear.gear_map))
                    source_data = [
                        {'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}}
                        for item in stored_data.values_list('object_id').distinct()]
                    is_first = gear.gear_map.last_sent_stored_data_id is None
                    entries = controller.send_stored_data(source_data, target_fields, is_first=is_first)
                    print("Result target: {0}".format(entries))
                    if entries:
                        gear.gear_map.last_source_update = timezone.now()
                        gear.gear_map.last_sent_stored_data_id = stored_data.order_by('-id').first().id
                        gear.gear_map.save()
        except Exception as e:
            raise
            print("Exception in task %s" % gear_id)
        finally:
            release_lock()
        return True
    return False