from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.controllers.filters import *
from apps.gp.enum import FilterEnum
from apps.gp.models import Connection, GearFilter
from apps.history.models import DownloadHistory, SendHistory
from django.core.serializers import serialize
from django.db.models import Q
from dateutil.parser import parse
from datetime import datetime
import logging
import httplib2
import json

logger = logging.getLogger('controller')


class FilterBaseController(object):
    def _get_gear_filters(self):
        return GearFilter.objects.filter(Q(gear__source=self._plug) | Q(gear__target=self._plug))

    def _apply_filter(self, filter, values):
        filter_method = FilterEnum.get_filter(FilterEnum(int(filter.option)))
        return filter_method(values, filter)

    def apply_filters(self, source_data):
        filters = self._get_gear_filters()
        new_source_data = source_data.copy()
        excluded_source_data = []
        if bool(filters):
            for f in filters:
                new_source_data, excluded_data = self._apply_filter(f, new_source_data)
                excluded_source_data.extend(excluded_data)
        return new_source_data, excluded_source_data


class BaseController(FilterBaseController):
    """
    Abstract controller class.
    - The init calls the create_connection method.

    """
    _connection_object = None
    _plug = None
    _connector = None
    _log = logging.getLogger('controller')

    def __init__(self, connection=None, plug=None, **kwargs):
        self.create_connection(connection=connection, plug=plug, **kwargs)

    def create_connection(self, connection=None, plug=None):
        """
            :param connection: can be either a base or specific connection.
            :param plug:
            :return:
        """
        if connection:
            if isinstance(connection, Connection):
                connection = connection.related_connection
            self._connection_object = connection
            try:
                self._connector = self._connection_object.connection.connector
            except:
                self._connector = None
        if plug:
            self._plug = plug
        return

    def test_connection(self):
        raise ControllerError('Not implemented yet.')

    def send_stored_data(self, *args, **kwargs):
        raise ControllerError('Not implemented yet.')

    def download_to_stored_data(self, connection_object, plug, **kwargs):
        raise ControllerError('Not implemented yet.')

    def download_source_data(self, connection_object=None, plug=None, **kwargs):
        """
        El DOWNLOAD_TO_STORED_DATA DEBE RETORNAR UNA LISTA CON DICTs (uno por cada dato enviado) CON ESTE FORMATO:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json, {'name':'value'}
             "is_stored": True | False},
             "identifier": {'name': '', 'value' :(%item identifier. EJ: ID) },
            {...}, {...},
         "last_source_record":(%last_order_by_value)},}
        :return: last_source_record
        """
        if connection_object is not None and plug is not None:
            self._connection_object = connection_object
            self._plug = plug
        if self._connection_object is not None and self._plug is not None:
            try:
                result = self.download_to_stored_data(self._connection_object, self._plug, **kwargs)
                try:
                    if isinstance(result, bool) and result is False:
                        return result
                    serialized_connection = serialize('json', [self._connection_object, ])
                    for item in result['downloaded_data']:
                        DownloadHistory.objects.create(gear_id=str(self._plug.gear_source.first().id),
                                                       plug_id=str(self._plug.id), connection=serialized_connection,
                                                       raw=json.dumps(item['raw']), connector_id=self._connector.id,
                                                       identifier=item['identifier'], )
                    return result['last_source_record']
                except KeyError:
                    print("no hay last source?? -> \t{0}".format(result))
                    return result
                except:
                    raise
                    print("NO REGISTRO DATA")
                    return False
            except TypeError:
                return self.download_to_stored_data(self._connection_object, self._plug)
        raise ControllerError(code=0, controller=self.connector.name,
                              message="Please check you're using a valid connection and a valid plug.")

    def send_target_data(self, source_data, target_fields, is_first=False, **kwargs):
        """
        El SEND_STORED_DATA DEBE RETORNAR UNA LISTA CON DICTs (uno por cada dato enviado) CON ESTE FORMATO:
        {'data': {(%dict del metodo 'get_dict_with_source_data')},
         'response': (%mensaje del resultado),
         'sent': True|False,
         'identifier': (%identificador del dato enviado. Ej: ID.)
        }
        """
        if self._connection_object is not None and self._plug is not None:
            source_data, excluded_source_data = self.apply_filters(source_data)
            data_list = get_dict_with_source_data(source_data, target_fields)
            excluded_data_list = get_dict_with_source_data(excluded_source_data, target_fields)
            if is_first and len(data_list) > 0:
                try:
                    data_list = [data_list[0]]
                except IndexError:
                    data_list = []
                except Exception as e:
                    raise ControllerError(message="Unexpected Exception. Please report this error: {}.".format(str(e)))
            if data_list:
                try:
                    result = self.send_stored_data(data_list, **kwargs)
                    serialized_connection = serialize('json', [self._connection_object, ])
                    for item in result:
                        SendHistory.objects.create(connector_id=self._connector.id, connection=serialized_connection,
                                                   gear_id=str(self._plug.gear_target.first().id),
                                                   plug_id=str(self._plug.id),
                                                   data=json.dumps(item['data']), response=item['response'],
                                                   sent=int(item['sent']), identifier=item['identifier'])
                    data_list_result = [i['identifier'] for i in result]
                except KeyError:
                    data_list_result = result
                except TypeError:
                    data_list_result = self.send_stored_data(source_data, target_fields, **kwargs)
            if excluded_data_list:
                serialized_connection = serialize('json', [self._connection_object, ])
                for item in excluded_data_list:
                    SendHistory.objects.create(connector_id=self._connector.id, connection=serialized_connection,
                                               gear_id=str(self._plug.gear_target.first().id),
                                               plug_id=str(self._plug.id), sent=2, identifier='-1',
                                               response='Item filtered by: {0}'.format(item.pop('__filter__',
                                                                                                'Filter not found')),
                                               data=json.dumps(item), )
                if not data_list:
                    return [-1, ]
            return data_list_result
        raise ControllerError(code=0, controller=self._connector.name,
                              message="Please check you're using a valid connection and a valid plug.")

    def get_target_fields(self, **kwargs):
        raise ControllerError('Not implemented yet.')

    def get_mapping_fields(self, **kwargs):
        raise ControllerError('Not implemented yet.')

    def get_action_specification_options(self, action_specification_id):
        raise ControllerError('Not implemented yet.')

    def create_webhook(self, **kwargs):
        raise ControllerError('Webhooks are not supported.')

    def do_webhook_process(self, **kwargs):
        raise ControllerError('Not implemented yet.')

    @property
    def connector(self):
        return self._connector

    @property
    def has_webhook(self):
        return False

    @property
    def has_test_information(self):
        return False


class GoogleBaseController(BaseController):
    def _upate_connection_object_credentials(self):
        self._connection_object.credentials_json = self._credential.to_json()
        self._connection_object.save(update_fields=['credentials_json'])

    def _refresh_token(self, **kwargs):
        if self._credential.access_token_expired:
            self._credential.refresh(httplib2.Http())
            self._upate_connection_object_credentials()

    def _report_broken_token(self, scale=None):
        print("IMPOSIBLE REFRESCAR EL TOKEN!!!! NOTIFICAR AL USUARIO.")
