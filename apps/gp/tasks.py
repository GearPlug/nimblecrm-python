from apps.gp.models import Gear, StoredData, GearMapData, Plug
from apps.gp.enum import ConnectorEnum
from apiconnector.celery import app
from django.core.cache import cache
from django.db.models import ObjectDoesNotExist
from django.utils import timezone

from collections import OrderedDict

LOCK_EXPIRE = 60 * 1


# @app.task(queue="beat")
@app.task
def update_all_gears():
    print("Starting to update all gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).prefetch_related()
    gear_amount = active_gears.count()
    print("A total of %s gears will be updated." % gear_amount)
    for gear in active_gears:
        connector = ConnectorEnum.get_connector(gear.source.connection.connector_id)
        # update_plug.s(gear.source.id, gear.id).apply_async(queue=connector.name.lower())  # CON COLAS
        update_plug.s(gear.source.id, gear.id).apply_async() # SIN COLAS
        print("Assigning plug {0} to queue: {1}.".format(gear.source.id, connector.name.lower()))


# @app.task(queue="connector")
@app.task
def update_plug(plug_id, gear_id, **query_params):
    plug = Plug.objects.get(pk=plug_id)
    gear = Gear.objects.get(pk=gear_id)
    lock_id = 'lock-{0}-gear'.format(plug.id)
    acquire_lock = lambda: cache.add(lock_id, 'true', LOCK_EXPIRE)
    release_lock = lambda: cache.delete(lock_id)
    if acquire_lock():
        print("Updating Plug: {0} from Gear: {1} as {2}".format(plug_id, gear_id, plug.plug_type))
        try:
            query_params = {'connection': gear.source.connection, 'plug': gear.source, }
            if gear.gear_map.last_sent_stored_data_id is not None:
                query_params['id__gt'] = gear.gear_map.last_sent_stored_data_id
            connector = ConnectorEnum.get_connector(plug.connection.connector.id)
            controller_class = ConnectorEnum.get_controller(connector)
            controller = controller_class(plug.connection.related_connection, plug)
            ping = controller.test_connection()
            if ping is not True:
                print("Error en la connection.")
                return
            if plug.plug_type.lower() == 'source':

                try:
                    plug.webhook
                    has_new_data = False
                    print("HAS WEBHOOK. DO NOT UPDATE.")
                except AttributeError as e:
                    print("LAST IS: {}".format(gear.gear_map.last_source_order_by_field_value))
                    has_new_data = controller.download_source_data(
                        last_source_record=gear.gear_map.last_source_order_by_field_value)
                print("download_result: {}".format(has_new_data))
                if has_new_data:
                    gear.gear_map.last_source_order_by_field_value = has_new_data
                    gear.gear_map.save(update_fields=['last_source_order_by_field_value', ])
                stored_data = StoredData.objects.filter(**query_params)
                if stored_data.count() > 0:
                    target_connector = ConnectorEnum.get_connector(gear.target.connection.connector_id)
                    update_plug.s(gear.target.id, gear_id).apply_async()  # SIN COLAS
                    # update_plug.s(gear.target.id, gear_id).apply_async(queue=target_connector.name.lower())  # CON COLAS
                    print("Assigning plug {0} to queue: {1}.".format(gear.target.id, connector.name.lower()))
            elif plug.plug_type.lower() == 'target':
                stored_data = StoredData.objects.filter(**query_params)
                if stored_data.count() > 0:
                    target_fields = OrderedDict((data.target_name, data.source_value) for data in
                                                GearMapData.objects.filter(gear_map=gear.gear_map))
                    source_data = [
                        {'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}}
                        for item in stored_data.values_list('object_id').distinct()]
                    is_first = gear.gear_map.last_sent_stored_data_id is None
                    entries = controller.send_stored_data(source_data, target_fields, is_first=is_first)
                    print("Result target: {0}".format(entries))
                    if entries or connector == ConnectorEnum.MailChimp:
                        gear.gear_map.last_source_update = timezone.now()
                        gear.gear_map.last_sent_stored_data_id = stored_data.order_by('-id').first().id
                        gear.gear_map.save(update_fields=['last_source_update', 'last_sent_stored_data_id'])
        except Exception as e:
            raise
            print("Exception in task %s" % gear_id)
        finally:
            release_lock()
        return True
    return False
