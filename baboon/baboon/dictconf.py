import sys
import logging

from baboon.common.config import get_log_path, get_null_handler


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
    }, {
        'args': ('--hostname',),
        'kwargs': {
            'help': 'override the default baboon-project.org hostname.',
            'dest': 'hostname',
            'default': 'baboon-project.org'
        }
    }, {
        'args': ('--config', ),
        'kwargs': {
            'help': 'override the default location of the configuration file.',
            'dest': 'configpath'
        }
    }],
    'subparsers': [
        {
            'name': 'register',
            'help': 'create an account.',
            'args': [{
                'args': ('username',),
                'kwargs': {
                    'help': 'your username.',
                    'nargs': '?'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to override the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'projects',
            'help': 'list all users in a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.',
                    'nargs': '?'
                }
            }, {
                'args': ('-a', '--all'),
                'kwargs': {
                    'help': 'display all information.',
                    'action': 'store_true'
                }
            }]
        }, {
            'name': 'create',
            'help': 'create a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('path',),
                'kwargs': {
                    'help': 'the project path on the filesystem.',
                    'action': 'store'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'delete',
            'help': 'delete a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'join',
            'help': 'join a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('path',),
                'kwargs': {
                    'help': 'the project path on the filesystem.',
                    'action': 'store'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'unjoin',
            'help': 'unjoin a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('--nosave', ),
                'kwargs': {
                    'help': 'avoid to dump the configuration file.',
                    'action': 'store_true',
                    'dest': 'nosave',
                    'default': False
                }
            }]
        }, {
            'name': 'accept',
            'help': 'accept a user to join a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('username',),
                'kwargs': {
                    'help': 'the username to accept.'
                }
            }]
        }, {
            'name': 'reject',
            'help': 'reject a user to join a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('username',),
                'kwargs': {
                    'help': 'the username to reject.'
                }
            }]
        }, {
            'name': 'kick',
            'help': 'kick a user from a project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('username',),
                'kwargs': {
                    'help': 'the username to kick.'
                }
            }]
        }, {
            'name': 'init',
            'help': 'initialize a new project.',
            'args': [{
                'args': ('project',),
                'kwargs': {
                    'help': 'the project name.'
                }
            }, {
                'args': ('git-url',),
                'kwargs': {
                    'help': 'the remote git url to fetch the project.'
                }
            }]
        }, {
            'name': 'start',
            'help': 'start Baboon !',
            'args': [{
                'args': ('--no-init',),
                'kwargs': {
                    'help': 'avoid to execute the startup sync.',
                    'dest': 'init',
                    'default': False,
                    'action': 'store_true'
                }
            }]
        }
    ]
}


LOGGING = {
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '%(message)s',
            'datefmt': '%Y/%m/%d %H:%M:%S'

        },
        'simple': {
            'format': '%(message)s'
        },
    },
    'handlers': {
        'rootfile': {
            'level': 'DEBUG',
            'class': get_null_handler(),
            'formatter': 'verbose'
        },
        'sleekxmppfile': {
            'class': get_null_handler(),
            'level': 'DEBUG',
            'formatter': 'verbose'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'baboon.common.loghandler.ConsoleUnixColoredHandler',
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
