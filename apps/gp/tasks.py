from apps.gp.models import Gear, StoredData, GearMapData, Plug
from apps.gp.enum import ConnectorEnum
from apiconnector.celery import app
from django.core.cache import cache
from django.utils import timezone
from collections import OrderedDict

LOCK_EXPIRE = 60 * 1


@app.task
def dispatch_all_gears():
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).values('id')
    print(1, active_gears)
    # TODO: AGREGAR FILTROS PARA COMPROBAR SI TIENE SOURCE Y TARGET. Y VALIDAR QUE EL MAPEO ES CORRECTO.
    # TODO: DESACTIVAR LOS GEARS QUE NO CUMPLAN LAS VALIDACIONES DE MAPEO O QUE NO TENGAN SOURCE Y TARGET. (EMAIL)
    for gear in active_gears:
        print("DISPATCH GEAR {}".format(gear['id']))
        dispatch.s(str(gear['id'])).apply_async(queue='dispatch')
        # dispatch.s(gear['id']).apply_async()
    return True


@app.task
def dispatch(gear_id):
    try:
        gear = Gear.objects.get(pk=gear_id)
        # TODO: SOURCE
        source = Plug.objects.filter(pk=gear.source.id).prefetch_related('connection__connector').first()  #
        source_connector = ConnectorEnum.get_connector(source.connection.connector.id)
        source_controller_class = ConnectorEnum.get_controller(source_connector)
        source_controller = source_controller_class(connection=source.connection.related_connection, plug=source)
        if source_controller.needs_polling:
            if source_controller.test_connection():
                print("Agregando el Plug: {0} ({1}) al queue: POLLING".format(source.id, source_controller.connector))
                result_s = do_poll.s(source.id).apply_async(queue='polling')
                # do_poll.s(source.id).apply_async()
            else:
                raise Exception("Desactivar gear por connection al tercer intento.")
        # TODO: TARGET
        query_params = {'connection_id': source.connection.id, 'plug_id': source.id, }
        target = Plug.objects.filter(pk=gear.target.id).prefetch_related('connection__connector').first()
        if gear.gear_map.last_sent_stored_data_id is not None:
            query_params['id__gt'] = gear.gear_map.last_sent_stored_data_id
        stored_data = StoredData.objects.filter(**query_params)
        if stored_data.count() > 0:
            print("Agregando el Plug: {0} ({1}) al queue: SEND".format(target.id, target.connection.connector.name))
            result_t = send_data.s(target.id, query_params).apply_async(queue='send')
            # result_t = send_data.s(target.id).apply_async()
        return True
    except:
        raise
        return False


@app.task
def do_poll(plug_id, time=0):
    try:
        source = Plug.objects.filter(pk=plug_id).prefetch_related('connection__connector').first()
        gear = Gear.objects.get(source_id=plug_id)
        source_connector = ConnectorEnum.get_connector(source.connection.connector.id)
        source_controller_class = ConnectorEnum.get_controller(source_connector)
        source_controller = source_controller_class(connection=source.connection.related_connection, plug=source)
        if source_controller.test_connection():
            last_order_by_value = gear.gear_map.last_source_order_by_field_value
            # TODO: ADD VALIDATIONS FOR THIS VALUE.
            last_source_record = source_controller.download_source_data(
                last_source_record=last_order_by_value)
            if last_source_record and last_source_record is not True:
                gear.gear_map.last_source_update = timezone.now()
                gear.gear_map.last_source_order_by_field_value = last_source_record
                gear.gear_map.save(update_fields=['last_source_order_by_field_value', 'last_source_update'])
                # TODO: hacer dispatch al gear inmediatamente para actualizar target.
                dispatch.s(str(gear.id)).apply_async(queue='dispatch')
        else:
            # TODO: IF THE TEST FAILS IT MAY BE A TEMPORAL ERROR. RETRY EXPONENTIALLY UP TO 32 SECONDS (3) AND CANCEL IT.
            return False
        return True
    except:
        raise
        return False


@app.task
def send_data(plug_id, params):
    try:
        target = Plug.objects.filter(pk=plug_id).prefetch_related('connection__connector').first()
        gear = Gear.objects.get(target_id=plug_id)
        stored_data = StoredData.objects.filter(**params)
        target_connector = ConnectorEnum.get_connector(target.connection.connector.id)
        target_controller_class = ConnectorEnum.get_controller(target_connector)
        target_controller = target_controller_class(connection=target.connection.related_connection, plug=target)
        target_fields = OrderedDict((data.target_name, data.source_value)
                                    for data in GearMapData.objects.filter(gear_map=gear.gear_map))
        source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}} for
                       item in stored_data.values_list('object_id').distinct()]
        is_first = gear.gear_map.last_sent_stored_data_id is None
        entries = target_controller.send_target_data(source_data, target_fields, is_first=is_first)
        last_sent_data = StoredData.objects.filter(object_id=source_data[-1]['id'], plug=gear.source,
                                                   connection=gear.source.connection).order_by('id').last()
        if entries or target_controller.connector == ConnectorEnum.MailChimp:
            gear.gear_map.last_sent_stored_data_id = last_sent_data.id
            gear.gear_map.save(update_fields=['last_sent_stored_data_id'])
        return True
    except:
        raise
        return False


@app.task
def update_all_gears():
    print("Starting to update all gears...")
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).prefetch_related()
    gear_amount = active_gears.count()
    print("A total of %s gears will be updated." % gear_amount)
    for gear in active_gears:
        connector = ConnectorEnum.get_connector(gear.source.connection.connector_id)
        # update_plug.s(gear.source.id, gear.id).apply_async(queue=connector.name.lower())  # CON COLAS
        update_plug.s(gear.source.id, gear.id).apply_async()  # SIN COLAS
        print("Assigning plug {0} to queue: {1}.".format(gear.source.id, connector.name.lower()))


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
            controller = controller_class(connection=plug.connection.related_connection, plug=plug)
            ping = controller.test_connection()
            if ping is not True:
                print("Error en la connection.")
                return
            if plug.plug_type.lower() == 'source':
                try:
                    if plug.webhook.is_active is True:
                        has_new_data = False
                    else:
                        raise AttributeError("El webhook esta desactivado")
                except AttributeError as e:
                    # print("LAST IS: {}".format(gear.gear_map.last_source_order_by_field_value))
                    has_new_data = controller.download_source_data(
                        last_source_record=gear.gear_map.last_source_order_by_field_value)
                # print("download_result: {}".format(has_new_data))
                if has_new_data and has_new_data is not True:
                    gear.gear_map.last_source_order_by_field_value = has_new_data
                    gear.gear_map.save(update_fields=['last_source_order_by_field_value', ])
                stored_data = StoredData.objects.filter(**query_params)
                print("count {}".format(stored_data.count()))
                if stored_data.count() > 0:
                    target_connector = ConnectorEnum.get_connector(gear.target.connection.connector_id)
                    update_plug.s(gear.target.id, gear_id).apply_async()  # SIN COLAS
                    # update_plug.s(gear.target.id, gear_id).apply_async(queue=target_connector.name.lower())  # CON COLAS
                    print("Assigning plug {0} to queue: {1}.".format(gear.target.id,
                                                                     gear.target.connection.connector.name.lower()))
            elif plug.plug_type.lower() == 'target':
                stored_data = StoredData.objects.filter(**query_params)
                if stored_data.count() > 0:
                    target_fields = OrderedDict((data.target_name, data.source_value) for data in
                                                GearMapData.objects.filter(gear_map=gear.gear_map))
                    source_data = [
                        {'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}} for
                        item in stored_data.values_list('object_id').distinct()]
                    is_first = gear.gear_map.last_sent_stored_data_id is None
                    entries = controller.send_target_data(source_data, target_fields, is_first=is_first)
                    last_sent_data = StoredData.objects.filter(object_id=source_data[-1]['id'], plug=gear.source,
                                                               connection=gear.source.connection).order_by('id').last()
                    if entries or connector == ConnectorEnum.MailChimp:
                        gear.gear_map.last_source_update = timezone.now()
                        gear.gear_map.last_sent_stored_data_id = last_sent_data.id
                        gear.gear_map.save(update_fields=['last_source_update', 'last_sent_stored_data_id'])
        except Exception as e:
            raise
            print("Exception in task %s" % gear_id)
        finally:
            release_lock()
        return True
    return False
