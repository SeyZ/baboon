import copy
import logging


class ConsoleUnixColoredHandler(logging.StreamHandler):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    COLORS = {
        'FATAL': RED,
        'ERROR': RED,
        'WARNING': YELLOW,
        'INFO': GREEN,
        'DEBUG': CYAN,
        }

    def emit(self, r):
        # Need to make a actual copy of the record to prevent altering
        # the message for other loggers.
        record = copy.copy(r)
        levelname = record.levelname

        # Configures the current colors to use.
        color = self.COLORS[record.levelname]

        # Colories the levelname of each log message
        record.levelname = self._get_fg_color(color) + str(levelname) + \
            self._reset()
        logging.StreamHandler.emit(self, record)

    def _get_fg_color(self, color):
        return '\x1B[1;3%sm' % color

    def _reset(self):
        return '\x1B[1;%sm' % self.BLACK


LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'rootfile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'simple',
            'filename': 'logs/root.log',
            'mode': 'a',
        },
        'sleekxmppfile': {
            'class': 'logging.handlers.RotatingFileHandler',
            'level': 'DEBUG',
            'formatter': 'verbose',
            'filename': 'logs/sleekxmpp.log',
            'mode': 'a',
            'maxBytes': 10485760,
            'backupCount': 5,
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logconf.ConsoleUnixColoredHandler',
            'formatter': 'simple',
            'stream': 'ext://sys.stdout',
        }
    },
    'loggers': {
        'baboon': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
        'sleekxmpp': {
            'handlers': ['sleekxmppfile'],
            'level': 'DEBUG',
        },
        'root': {
            'handlers': ['rootfile'],
            'level': 'DEBUG',
        },
    }
}
