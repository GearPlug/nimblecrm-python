from apps.gp.controllers.exception import ControllerError
from apps.gp.models import Connection
import logging
import httplib2

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
        if self._connection_object is not None and self._plug is not None:
            try:
                return self.download_to_stored_data(self._connection_object,
                                                    self._plug, **kwargs)
            except TypeError:
                print("CLASS TO FIX: {}".format(self))
                return self.download_to_stored_data(self._connection_object,
                                                    self._plug)

        else:
            raise ControllerError("There's no active connection or plug.")

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

    def _refresh_token(self, token=''):
        if self._credential.access_token_expired:
            self._credential.refresh(httplib2.Http())
            self._upate_connection_object_credentials()

    def _report_broken_token(self, scale=None):
        print("IMPOSIBLE REFRESCAR EL TOKEN!!!! NOTIFICAR AL USUARIO.")

