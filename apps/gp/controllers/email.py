from apps.gp.controllers.base import BaseController
from apps.gp.controllers.exception import ControllerError
from apps.gp.controllers.utils import get_dict_with_source_data
from utils.smtp_sender import smtpSender as SMTPClient


class GmailController(BaseController):
    pass


class SMTPController(BaseController):
    client = None
    sender_identifier = 'ZAKARA .23'

    def create_connection(self, *args, **kwargs):
        if args:
            super(SMTPController, self).create_connection(*args)
            if self._connection_object is not None:
                try:
                    host = self._connection_object.host
                    port = self._connection_object.port
                    user = self._connection_object.connection_user
                    password = self._connection_object.connection_password
                    self.client = SMTPClient(host, port, user, password)
                except Exception as e:
                    print("Error getting the SMS attributes")
                    print(e)
        elif kwargs:
            host = kwargs['host']
            port = kwargs['port']
            user = kwargs['connection_user']
            password = kwargs['connection_password']
            self.client = SMTPClient(host, port, user, password)

        return self.client.is_valid_connection() if self.client else None

    def get_target_fields(self, **kwargs):
        return ['recipient', 'message']

    def send_stored_data(self, source_data, target_fields, is_first=False):
        obj_list = []
        data_list = get_dict_with_source_data(source_data, target_fields)
        if is_first:
            if data_list:
                try:
                    data_list = [data_list[-1]]
                except:
                    data_list = []
        if self._plug is not None:
            for obj in data_list:
                r = self.client.send_mail(**obj)
            extra = {'controller': 'smtp'}
            return
        raise ControllerError("Incomplete.")
