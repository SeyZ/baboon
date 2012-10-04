

class CommandException(Exception):

    def __init__(self, status_code, msg):
        self.status_code = status_code
        self.msg = msg

    def __repr__(self):
        print("%s - %s" % (self.status_code, self.msg))


class BaboonException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)
