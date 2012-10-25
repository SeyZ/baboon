import os
import sys
import argparse

from logging import Handler
from os.path import join, dirname, abspath, expanduser, exists, isfile, isdir
from baboon.common.errors.baboon_exception import ConfigException

if sys.version_info < (2, 7):
    from baboon.common.thirdparty.dictconfig import dictConfig
else:
    from logging.config import dictConfig

if sys.version_info < (3, 0):
    from ConfigParser import RawConfigParser, Error as ConfigParserError
else:
    from configparser import RawConfigParser, Error as ConfigParserError


class NullHandler(Handler):
    """ Reimplemented the NullHandler logger for Python < 2.7.
    """

    def emit(self, record):
        pass


def get_null_handler():
    """ Return the module path of the NullHandler. Useful for Python < 2.7.
    """

    # NullHandler does not exist before Python 2.7
    null_handler_mod = 'logging.NullHandler'
    try:
        from logging import NullHandler
    except ImportError:
        null_handler_mod = 'baboon.common.config.NullHandler'

    return null_handler_mod


def get_config_path(arg_attrs, config_name):
    """ Gets the configuration path with the priority order:
    1) config command line argument
    2) <project_path>/conf/baboonrc
    3) ~/.baboonrc
    4) /etc/baboon/baboonrc
    5) environment variable : BABOONRC
    Otherwise : return None

    arg_attrs is the parser argument attributes.
    config_name is the name of the configuration file.
    """

    # Verify if the config path is specified in the command line.
    config_path = arg_attrs.get('configpath')
    if config_path:
        return config_path

    mod_path = _get_module_path()
    curdir_path = '%s/conf/%s' % (mod_path, config_name)
    user_path = '%s/.%s' % (expanduser('~'), config_name)
    etc_path = '/etc/baboon/%s' % config_name

    # Verify if one of the config paths (etc, user and curdir) exist.
    for loc in etc_path, user_path, curdir_path:
        if isfile(loc):
            return loc

    # Otherwise, return the env BABOONRC variable or None.
    return os.environ.get("BABOONRC")


def get_config_file(arg_attrs, config_name):
    """ Returns the dict corresponding to the configuration file.
    """

    filename = get_config_path(arg_attrs, config_name)
    if not filename:
        raise ConfigException("Failed to retrieve the configuration filepath.")

    try:
        parser = RawConfigParser()
        parser.read(filename)

        file_attrs = {}
        for section in parser.sections():
            file_attrs[section] = dict(parser.items(section))

        return file_attrs
    except ConfigParserError:
        raise ConfigException("Failed to parse the configuration file: %s " %
                              filename)


def init_config_log(arg_attrs, logconf):
    """ Configures the logger level setted in the logging args
    """

    # Ensure the log directory exists.
    try:
        mod_path = _get_module_path()
        log_dir = join(mod_path, 'logs')
        if not isdir(log_dir):
            os.makedirs(log_dir)
    except EnvironmentError:
        raise ConfigException("Cannot create the logs directory")

    # Configure the logger with the dict logconf.
    logconf['loggers']['baboon']['level'] = arg_attrs['loglevel']
    dictConfig(logconf)


def get_config_args(parser_dict):
    """ Builds and returns the argument parser.
    """

    # Create the new global parser.
    parser = argparse.ArgumentParser(description=parser_dict['description'])

    # Add arguments to the global parser.
    for arg in parser_dict['args']:
        parser.add_argument(*arg['args'], **arg['kwargs'])

    # Iterates over all subparsers.
    if parser_dict['subparsers']:
        subparsers = parser.add_subparsers()
    for item in parser_dict['subparsers']:
        # Add the new subparser.
        subparser = subparsers.add_parser(item['name'], help=item['help'])
        subparser.set_defaults(which=item['name'])

        # Add arguments to the subparser.
        for arg in item['args']:
            subparser.add_argument(*arg['args'], **arg['kwargs'])

    args = parser.parse_args()

    # Ensure the path is an abspath.
    if hasattr(args, 'path') and args.path:
        args.path = abspath(expanduser(args.path))

    # Return a dict, not a Namespace.
    return args.__dict__


def get_log_path():
    """ Returns the correct log directory path.
    """

    # The log directory to use if there's a problem.
    fallback_logdir = expanduser('~/')

    if os.name == 'posix':
        try:
            var_log = '/var/log/baboon'
            if not os.path.exists(var_log):
                os.makedirs(var_log)
            return var_log if os.path.isdir(var_log) else fallback_logdir
        except EnvironmentError:
            pass

    return fallback_logdir


def _get_module_path():
    return dirname(dirname(abspath(__file__)))
