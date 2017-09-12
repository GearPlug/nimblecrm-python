class ControllerError(Exception):
    def __init__(self, code=None, controller='', message=''):
        self.code = code
        self.message = message
        self.controller = controller
        super(ControllerError, self).__init__(
            'Code: {0}. Controller: {1} \nMessage: {1}.'.format(self.code, self.controller, self.message))
