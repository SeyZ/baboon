

class CommandException(Exception):

    def __init__(self, status_code, msg=None):
        super(CommandException, self).__init__(msg)
        self.status_code = status_code


class BaboonException(Exception):
    pass


class ForbiddenException(BaboonException):
    pass


class ConfigException(BaboonException):
    pass
