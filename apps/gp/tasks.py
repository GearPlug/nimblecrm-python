from apps.gp.models import Gear, StoredData, GearMapData, Plug
from apps.gp.enum import ConnectorEnum
from apiconnector.celery import app
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone, dateparse
from collections import OrderedDict
import redis

REDIS_HOST = 'localhost'
REDIS_PORT = '6379'


@app.task
def dispatch_all_gears():
    active_gears = Gear.objects.filter(is_active=True, gear_map__is_active=True).values('id')
    # TODO: AGREGAR FILTROS PARA COMPROBAR SI TIENE SOURCE Y TARGET. Y VALIDAR QUE EL MAPEO ES CORRECTO.
    # TODO: DESACTIVAR LOS GEARS QUE NO CUMPLAN LAS VALIDACIONES DE MAPEO O QUE NO TENGAN SOURCE Y TARGET. (EMAIL)
    for gear in active_gears:
        res = dispatch.s(gear['id']).apply_async()
        # res = dispatch.s(str(gear['id'])).apply_async(queue='dispatch')
        print("DISPATCH GEAR {0} WITH TASK [{1}]".format(gear['id'], res.task_id))
        #
    return True


@app.task(bind=True, max_retries=5, soft_time_limit=45, time_limit=50, )
def dispatch(self, gear_id, skip_source=False):
    con = redis.StrictRedis(REDIS_HOST, REDIS_PORT, db=0, charset="utf-8", decode_responses=True)
    NOW = timezone.now()
    try:
        gear = Gear.objects.get(pk=gear_id)
        source = Plug.objects.filter(pk=gear.source.id).prefetch_related('connection__connector').first()  #
        if skip_source is False:  # TODO: SOURCE
            source_connector = ConnectorEnum.get_connector(source.connection.connector.id)
            source_controller_class = ConnectorEnum.get_controller(source_connector)
            source_controller = source_controller_class(connection=source.connection.related_connection, plug=source)
            # TODO: VALIDAR QUE SE INSTANCIE BIEN SINO DESACTIVAR.
            if source_controller.needs_polling:
                if source_controller.test_connection():
                    source_task_name = "lock-{0}-task-plug".format(source.id)
                    existing_task = con.hgetall(source_task_name)
                    if not existing_task:
                        con.hmset(source_task_name, {"task": source.id, 'initial-time': NOW})
                        result_s = do_poll.s(source.id).apply_async()
                        # result_s = do_poll.s(source.id).apply_async(queue='polling')
                        print("Agregando el Plug: {0} ({1}) al queue: POLLING. \nTASK: [{2}]"
                              "".format(source.id, source_controller.connector, result_s.task_id))
                    else:
                        if 'initial-time' in existing_task.keys():
                            task_date = dateparse.parse_datetime(existing_task['initial-time'])
                            valid_through = task_date + timezone.timedelta(minutes=1)
                            if NOW > valid_through:
                                print("Task has taken to much time. Try to cancel.")
                                con.delete(source_task_name)
                                # TODO: CHECK THIS TASK AND REMOVE IT.
                        print("This plug's source seems to be updating already.")
                else:
                    if self.request.retries >= 5:
                        gear.is_active = False
                        gear.save(update_fields=['is_active', ])
                        # TODO: EMAIL NOTIFICAR GEAR APAGADO.
                        m = 'Hello, your GEAR {0} [{1}] has been deactivated due to an error with your source connection {2}[' \
                            '{3}].\nPlease review your connection is still valid and turn on your Gear again.\n' \
                            '{4}'.format(gear.name, gear.id, source_controller.connector, source.connection.id,
                                         settings.CURRENT_HOST)
                        send_notification_email.s(m, 'Deactivated Gear', recipient=gear.user.email).apply_async()
                        # send_notification_email.s(m, 'Deactivated Gear', recipient=gear.user.email).apply_async(
                        #     queue='misc')
                    else:
                        next_retry = 2 ** (self.request.retries + 1)
                        print("Retrying [{0}] in: {1} seconds.".format(self.request.retries, next_retry))
                        raise self.retry(countdown=next_retry)
                    return False
        # TODO: TARGET
        query_params = {'connection_id': source.connection.id, 'plug_id': source.id, }
        target = Plug.objects.filter(pk=gear.target.id).prefetch_related('connection__connector').first()
        if gear.gear_map.last_sent_stored_data_id is not None:
            query_params['id__gt'] = gear.gear_map.last_sent_stored_data_id
        stored_data = StoredData.objects.filter(**query_params)
        if stored_data.count() > 0:
            print("Agregando el Plug: {0} ({1}) al queue: SEND".format(target.id, target.connection.connector.name))
            target_task_name = "lock-{0}-task-plug".format(target.id)
            existing_task = con.hgetall(target_task_name)
            if not existing_task:
                con.hmset(target_task_name, {"task": target.id, 'initial-time': NOW})
                result_t = send_data.s(target.id, query_params).apply_async()
                # result_t = send_data.s(target.id, query_params).apply_async(queue='send')
                print("Agregando el Plug: {0} ({1}) al queue: SEND. \nTASK: [{2}]"
                      "".format(source.id, target.connection.connector.name, result_t.task_id))
            else:
                if 'initial-time' in existing_task.keys():
                    task_date = dateparse.parse_datetime(existing_task['initial-time'])
                    valid_through = task_date + timezone.timedelta(minutes=1)
                    if NOW > valid_through:
                        con.delete(target_task_name)
                        # TODO: CHECK THIS TASK AND REMOVE IT.
                print("This plug's target seems to be sending data already.")
        return True
    except Exception as e:
        # raise
        print(e)
        return False


@app.task(bind=True, max_retries=6, soft_time_limit=110, time_limit=120, )
def do_poll(self, plug_id):
    con = redis.StrictRedis(REDIS_HOST, REDIS_PORT, db=0, charset="utf-8", decode_responses=True)
    task_name = "lock-{0}-task-plug".format(plug_id)
    try:
        source = Plug.objects.filter(pk=plug_id).prefetch_related('connection__connector').prefetch_related(
            'connection').prefetch_related('user').first()
        gear = Gear.objects.get(source_id=plug_id)
        print("POLLING DATA FROM: {0} from GEAR [{1}]".format(source.connection.connector.name, gear.id))
        source_connector = ConnectorEnum.get_connector(source.connection.connector.id)
        source_controller_class = ConnectorEnum.get_controller(source_connector)
        source_controller = source_controller_class(connection=source.connection.related_connection, plug=source)
        # TODO: VALIDAR QUE SE INSTANCIE BIEN SINO DESACTIVAR.
        if source_controller.test_connection():
            last_order_by_value = gear.gear_map.last_source_order_by_field_value
            # TODO: ADD VALIDATIONS FOR THIS VALUE.
            last_source_record = source_controller.download_source_data(last_source_record=last_order_by_value)
            if last_source_record and last_source_record is not True:
                gear.gear_map.last_source_update = timezone.now()
                gear.gear_map.last_source_order_by_field_value = last_source_record
                gear.gear_map.save(update_fields=['last_source_order_by_field_value', 'last_source_update'])
                result = dispatch.s(str(gear.id), skip_source=True).apply_async()
                # result = dispatch.s(str(gear.id), skip_source=True).apply_async(queue='dispatch')
                return True
        else:
            if self.request.retries >= 6:
                print("Ya hay muchos retries. desactivar el gear y notificar al usuario.")
                gear.is_active = False
                gear.save(update_fields=['is_active', ])
                # TODO: EMAIL NOTIFICAR GEAR APAGADO.
                m = 'Hello, your GEAR {0} [{1}] has been deactivated due to an error with your source connection {2}[' \
                    '{3}].\nPlease review your connection is still valid and turn on your Gear again.\n' \
                    '{4}'.format(gear.name, gear.id, source_controller.connector, source.connection.id,
                                 settings.CURRENT_HOST)
                send_notification_email.s(m, 'Deactivated Gear', recipient=gear.user.email).apply_async()
                # send_notification_email.s(m, 'Deactivated Gear', recipient=gear.user.email).apply_async(queue='misc')
            else:
                next_retry = 2 ** (self.request.retries + 1)
                print("Retrying [{0}] in: {1} seconds.".format(self.request.retries, next_retry))
                raise self.retry(countdown=next_retry)
            return False
    except Exception as e:
        raise
        print(e, "EXCEPTION RAISED FOR GEAR [{0}] - PLUG [{1}] - CONNECTION [{2}]".format(gear.id, plug_id,
                                                                                          source.connection.id))
        return False
    finally:
        con.delete(task_name)


@app.task(bind=True, max_retries=6, soft_time_limit=110, time_limit=120, )
def send_data(self, plug_id, params):
    con = redis.StrictRedis(REDIS_HOST, REDIS_PORT, db=0)
    task_name = "lock-{0}-task-plug".format(plug_id)
    try:
        target = Plug.objects.filter(pk=plug_id).prefetch_related('connection__connector').prefetch_related(
            'connection').prefetch_related('user').first()
        gear = Gear.objects.get(target_id=plug_id)
        print("SENDING DATA TO: {0} from GEAR [{1}]".format(target.connection.connector.name, gear.id))
        stored_data = StoredData.objects.filter(**params)
        target_connector = ConnectorEnum.get_connector(target.connection.connector.id)
        target_controller_class = ConnectorEnum.get_controller(target_connector)
        target_controller = target_controller_class(connection=target.connection.related_connection, plug=target)
        if target_controller.test_connection():
            # Gearmap falta ordenar por versiones
            version = GearMapData.objects.filter(gear_map=gear.gear_map).order_by('-version').values('version')[0][
                'version']
            target_fields = OrderedDict((data.target_name, data.source_value)
                                        for data in
                                        GearMapData.objects.filter(gear_map=gear.gear_map, version=version))
            source_data = [{'id': item[0], 'data': {i.name: i.value for i in stored_data.filter(object_id=item[0])}} for
                           item in stored_data.values_list('object_id').distinct()]
            is_first = gear.gear_map.last_sent_stored_data_id is None
            entries = target_controller.send_target_data(source_data, target_fields, is_first=is_first)
            last_sent_data = StoredData.objects.filter(object_id=source_data[-1]['id'], plug=gear.source,
                                                       connection=gear.source.connection).order_by('id').last()
            if entries or target_controller.connector == ConnectorEnum.MailChimp:
                gear.gear_map.last_sent_stored_data_id = last_sent_data.id
                gear.gear_map.save(update_fields=['last_sent_stored_data_id'])
                # dispose_gear_stored_data.s(gear.id).apply_async(queue="misc")
            return True
        else:
            if self.request.retries >= 6:
                print("Ya hay muchos retries. desactivar el gear y notificar al usuario.")
                gear.is_active = False
                gear.save(update_fields=['is_active', ])
                # TODO: EMAIL NOTIFICAR GEAR APAGADO.
                m = 'Hello, your GEAR {0} [{1}] has been deactivated due to an error with your target connection {2}[' \
                    '{3}].\nPlease review your connection is still valid and turn on your Gear again.\n' \
                    '{4}'.format(gear.name, gear.id, target_controller.connector, target.connection.id,
                                 settings.CURRENT_HOST)
                send_notification_email.s(m, 'Deactivated Gear', recipient=gear.user.email).apply_async()
                # send_notification_email.s(m, 'Deactivated Gear', recipient=gear.user.email).apply_async(queue='misc')
            else:
                next_retry = 2 ** (self.request.retries + 1)
                print("Retrying [{0}] in: {1} seconds.".format(self.request.retries, next_retry))
                raise self.retry(countdown=next_retry)
            return False
    except Exception as e:
        raise
        print(e, "EXCEPTION RAISED FOR GEAR [{0}] - PLUG [{1}] - CONNECTION [{2}]".format(gear.id, plug_id,
                                                                                          target.connection.id))
        return False
    finally:
        con.delete(task_name)


@app.task(bind=True, soft_time_limit=40, time_limit=45, )
def send_notification_email(self, message, subject, recipient=None, recipient_list=[], from_email=None, ):
    if from_email is None:
        from_email = settings.DEFAULT_FROM_EMAIL
    if recipient is not None:
        try:
            recipient_list.append(recipient)
        except:
            recipient_list = []
    if recipient_list:
        return send_mail(subject, message, from_email, recipient_list)
    return False


@app.task(bind=True)
def dispose_gear_stored_data(self, gear_id):
    gear = Gear.objects.filter(pk=gear_id).prefetch_related('source', 'gear_map__gear_map_data')
    source = gear[0].source
    # TODO: FILTRAR POR CANTIDAD: SOLO DEJAR UNO #TODO: FILTRAR POR CANTIDAD: SOLO DEJAR UNO
    sd = StoredData.objects.filter(connection_id=source.connection, plug=source)
    sd = sd.exclude(object_id=sd.last().object_id)
    sd.delete()
