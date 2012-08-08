import os
import sys

if sys.version_info < (2, 7):
    from common.thirdparty.dictconfig import dictConfig
else:
    from logging.config import dictConfig

from ConfigParser import RawConfigParser


class Config(object):
    """ Singleton configuration class
    """

    def __init__(self, arg_parser, logconf, config_name='baboonrc'):

        self.arg_parser = arg_parser
        self.logconf = logconf
        self.config_name = config_name

        # The dict of all attributes
        self.attrs = {}

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

        etc_path = '/etc/baboonrc/%s' % self.config_name
        user_path = '%s/.%s' % (os.path.expanduser('~'), self.config_name)
        curdir_path = '%s/conf/%s' % (os.curdir, self.config_name)

        for loc in etc_path, user_path, curdir_path:
            if os.path.isfile(loc):
                return loc

        # if there's no good path, use the global environment
        # elsewhere, return None.
        return os.environ.get("BABOONRC")

    def _init_config_arg(self):
        """ Parse the command line arguments and inject values into the
        attrs['parser'] dict.
        """

        args = self.arg_parser.args
        self.attrs['parser'] = args.__dict__

    def _init_logging(self):
        """ Configures the logger level setted in the logging args
        """
        try:
            log_dir = os.path.join(os.getcwd(), 'logs')
            if not os.path.exists(log_dir):
                os.mkdir(log_dir)
        except IOError:
            sys.stderr.write("Cannot create the logs directory\n")
            exit(1)

        try:
            self.logconf['loggers']['baboon']['level'] = \
                    self.attrs['parser']['loglevel']
            dictConfig(self.logconf)
        except:
            sys.stderr.write("Failed to parse the logging config file\n")
            exit(1)

    def _init_config_file(self):
        filename = self._get_config_path()
        parser = RawConfigParser()
        parser.read(filename)

        self.attrs.update(parser._sections)
