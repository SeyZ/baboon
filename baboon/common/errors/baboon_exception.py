

class CommandException(Exception):

    def __init__(self, status_code, msg):
        self.status_code = status_code
        self.msg = msg

    def __repr__(self):
        print("%s - %s" % (self.status_code, self.msg))


class BaboonException(BaseException):
    pass


class ForbiddenException(BaboonException):
    pass


class ConfigException(BaboonException):
    pass
