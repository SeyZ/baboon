import logging


class ColorTerminal(object):
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ = "\033[1m"

    def formatter_message(self, msg, use_color=True):
        if use_color:
            msg = msg.replace("$RESET", self.RESET_SEQ)
            msg = msg.replace("$BOLD", self.BOLD_SEQ)
        else:
            msg = msg.replace("$RESET", "").replace("$BOLD", "")
        return msg


class ColorFormatter(logging.Formatter):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    COLORS = {
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': CYAN,
        'CRITICAL': MAGENTA,
        'ERROR': RED
    }

    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        levelname = record.levelname
        if self.use_color and levelname in self.COLORS:
            levelname_color = ColorTerminal.COLOR_SEQ % \
                (30 + self.COLORS[levelname]) + \
                levelname + ColorTerminal.RESET_SEQ
            record.levelname = levelname_color
        return logging.Formatter.format(self, record)


class BaboonLogger(logging.Logger):
    FORMAT = """%(levelname)-18s $BOLD%(name)-20s$RESET \
%(message)s ($BOLD%(filename)s$RESET:%(lineno)d)"""

    colorTerm = ColorTerminal()
    COLOR_FORMAT = colorTerm.formatter_message(FORMAT, True)

    def __init__(self, name):
        logging.Logger.__init__(self, name)

        color_formatter = ColorFormatter(self.COLOR_FORMAT)

        console = logging.StreamHandler()
        console.setFormatter(color_formatter)

        self.addHandler(console)
        return

    @staticmethod
    def setLoggerLevel(logger, level):
        log = logging.getLogger(logger)
        log.setLevel(level)


def logger(theclass):
    """ Adds a logger instance attribute to the class 'theclass'.
    By default, the logger is based on the name class.

    @param theclass: the instance of theclass will contains the new logger
    attribute
    """
    def new(cls, *args, **kwargs):
        result = super(cls, cls).__new__(cls)
        setattr(result, 'logger',
                logging.getLogger(cls.__name__))
        return result

    theclass.__new__ = staticmethod(new)
    return theclass
