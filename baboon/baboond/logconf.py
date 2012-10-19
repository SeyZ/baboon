import logging


PARSER = {
    'description': 'detect merge conflicts in realtime.',
    'args': [{
        'args': ('-v', '--verbose'),
        'kwargs': {
            'help': 'increase the verbosity.',
            'action': 'store_const',
            'dest': 'loglevel',
            'const': logging.DEBUG,
            'default': logging.INFO
        }
    }],
    'subparsers': []
}

LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(asctime)-20s%(levelname)-18s %(message)s'
            ' (%(threadName)s/%(funcName)s:%(lineno)s)',
            'datefmt': '%Y/%m/%d %H:%M:%S'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'rootfile': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'formatter': 'verbose',
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
            'class': 'baboon.common.logconf.ConsoleUnixColoredHandler',
            'formatter': 'verbose',
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
