import os
import sys
import logging
import logging.config

from ConfigParser import RawConfigParser


class Config(object):
    """ Singleton configuration class
    """

    def __init__(self, arg_parser, logconf):

        self.arg_parser = arg_parser
        self.logconf = logconf

        # configures the default path
        self.path = os.path.abspath(".")

        # init the configuration
        self.init_config()

    def init_config(self):
        """ Initializes:
        - the argument parser
        - the baboon configuration file
        - the watched project configuration file

        and puts all configurations in the config dict
        """

        if self.arg_parser:
            self._init_config_arg()

        self._init_logging()
        self._init_config_file()

    def _get_config_path(self):
        """ Gets the configuration path with the priority order :
        1) config command line argument
        2) <project_path>/conf/baboonrc
        3) ~/.baboonrc
        4) /etc/baboon/baboonrc
        5) environment variable : BABOONRC

        elsewhere : return None
        """

        if hasattr(self, 'configpath') and self.configpath:
            return self.configpath

        config_name = 'baboonrc'

        etc_path = '/etc/baboonrc/%s' % config_name
        user_path = '%s/.%s' % (os.path.expanduser('~'), config_name)
        curdir_path = '%s/conf/%s' % (os.curdir, config_name)

        for loc in etc_path, user_path, curdir_path:
            if os.path.isfile(loc):
                return loc

        # if there's no good path, use the global environment
        # elsewhere, return None.
        return os.environ.get("BABOONRC")

    def _init_config_arg(self):
        try:
            args = self.arg_parser.args

            # Iterates on all args items and store them into self.
            for arg in args.__dict__.iteritems():
                setattr(self, arg[0], arg[1])

        except AttributeError:
            sys.stderr.write("Failed to parse arguments\n")
            exit(1)

    def _init_logging(self):
        """ configures the logger level setted in the logging args
        """
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            if not os.path.exists(log_dir):
                os.mkdir(log_dir)
        except IOError:
            sys.stderr.write("Cannot create the logs directory\n")
            exit(1)

        try:
            self.logconf['loggers']['baboon']['level'] = self.loglevel
            logging.config.dictConfig(self.logconf)
        except:
            sys.stderr.write("Failed to parse the logging config file\n")
            exit(1)

    def _init_config_file(self):
        filename = self._get_config_path()
        parser = RawConfigParser()
        parser.read(filename)

        for section in parser.sections():
            for item in parser.items(section):
                if not hasattr(self, item[0]):
                    setattr(self, item[0], item[1])
