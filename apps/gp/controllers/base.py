import logging
from apps.gp.controllers.exception import ControllerError
from apps.gp.models import Action, ActionSpecification

logger = logging.getLogger('controller')


class BaseController(object):
    """
    Abstract controller class.
    - The init calls the create_connection method.

    """
    _connection_object = None
    _plug = None
    _log = logging.getLogger('controller')
    _connector = None

    def __init__(self, *args, **kwargs):
        self.create_connection(*args, **kwargs)

    def create_connection(self, *args):
        """
        El args[0] debe ser la connection (especifica).
        El args[1] puede ser el Plug o None.

        :param args:
        :return:
        """
        if args:
            self._connection_object = args[0]
            try:
                self._connector = self._connection_object.connector
            except:
                pass
            try:
                self._plug = args[1]
            except:
                pass
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
                return self.download_to_stored_data(self._connection_object, self._plug, **kwargs)
            except TypeError:
                print("CLASS TO FIX: {}".format(self))
                return self.download_to_stored_data(self._connection_object, self._plug)

        else:
            raise ControllerError("There's no active connection or plug.")

    def get_target_fields(self, **kwargs):
        raise ControllerError('Not implemented yet.')

    def get_mapping_fields(self, **kwargs):
        raise ControllerError('Not implemented yet.')

    def get_action_specification_options(self, action_specification_id):
        raise ControllerError('Not implemented yet.')

    def do_webhook_process(self,**kwargs):
        raise ControllerError('Not implemented yet.')