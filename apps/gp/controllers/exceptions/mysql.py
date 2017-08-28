from apps.gp.controllers.exception import ControllerError


class MySQLError(ControllerError):
    def __init__(self, *args, **kwargs):
        self.code = None
        self.msg = None

        if 'code' in kwargs:
            self.code = kwargs['code']
        if 'msg' in kwargs:
            self.msg = kwargs['msg']
