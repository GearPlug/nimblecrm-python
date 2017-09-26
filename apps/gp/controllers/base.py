from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from apps.gp.models import Connection, DownloadHistory, SendHistory
from django.core.serializers import serialize
import logging
import httplib2
import json

logger = logging.getLogger('controller')


class BaseController(object):
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

    def download_source_data(self, **kwargs):
        """
        El SEND_STORED_DATA DEBE RETORNAR UNA LISTA CON DICTs (uno por cada dato enviado) CON ESTE FORMATO:
        {'downloaded_data':[
            {"raw": "(%all_data_received_in_str_format)" # -> formato json,
             "data": {"unique": {"name": (%stored_data_unique_field_name), "value": (%stored_data_object_id),
                     "fields": [{"name": (%stored_data_name), "value": (%stored_data_value), ]} # -> formato json,
             "is_stored": True | False}]
         "last_source_record":(%last_order_by_value)},:
        :return: last_source_record
        """
        if self._connection_object is not None and self._plug is not None:
            try:
                result = self.download_to_stored_data(self._connection_object, self._plug, **kwargs)
                try:
                    if isinstance(result, bool) and result is False:
                        return result
                    serialized_connection = serialize('json', [self._connection_object, ])
                    for item in result['downloaded_data']:
                        print(self.connector)
                        DownloadHistory.objects.create(gear_id=str(self._plug.gear_source.first().id),
                                                       plug_id=str(self._plug.id), connection=serialized_connection,
                                                       raw=json.dumps(item['raw']),
                                                       saved_data=json.dumps(item['data']['fields']),
                                                       connector=self.connector)
                    return result['last_source_record']
                except:
                    print("NO REGISTRO DATA")
                    return result
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
            data_list = get_dict_with_source_data(source_data, target_fields)
            if is_first:
                try:
                    data_list = [data_list[-1]]
                except IndexError:
                    data_list = []
                except Exception as e:
                    raise ControllerError(message="Unexpected Exception. Please report this error: {}.".format(str(e)))
            print("DATALIST: len={}.".format(len(data_list)))
            try:
                result = self.send_stored_data(data_list, **kwargs)
                serialized_connection = serialize('json', [self._connection_object, ])
                for item in result:
                    SendHistory.objects.create(connector=self.connector, gear_id=str(self._plug.gear_target.first().id),
                                               plug_id=str(self._plug.id), connection=serialized_connection,
                                               data=json.dumps(item['data']), response=item['response'],
                                               sent=item['sent'], identifier=item['identifier'])

                return [i['identifier'] for i in result]
            except KeyError:
                return result
            except TypeError:
                return self.send_stored_data(source_data, target_fields, **kwargs)
        raise ControllerError(code=0, controller=self.connector.name,
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
