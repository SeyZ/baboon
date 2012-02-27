import os
import sys
import argparse
import logging

from utils import singleton
from ConfigParser import RawConfigParser
from errors.baboon_exception import BaboonException


class ArgumentParser(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Baboon ! Ook !')
        parser.add_argument('--path', metavar='path',
                          help='Specify the path you want to monitor')
        parser.add_argument('--config', metavar='config',
                            help='Override the default location of the \
                                config file')
        parser.add_argument('init', metavar='init', nargs='?', default=False,
                            type=bool, help='Initialize the baboon metadata')

        # logging args
        parser.add_argument('-d', '--debug', help='set logging to DEBUG',
                            action='store_const',
                            dest='loglevel',
                            const=logging.DEBUG,
                            default=logging.INFO)

        self.args = parser.parse_args()

        # configures the logger level setted in the logging args
        from logger import ColorLogger
        logging.basicConfig()

        handler = logging.getLogger().handlers[0]
        logging.getLogger().removeHandler(handler)

        logging.setLoggerClass(ColorLogger)
        logging.getLogger().setLevel(self.args.loglevel)


@singleton
class Config(object):
    """ Singleton configuration class
    """

    def __init__(self):
        # configures the default path
        self.path = os.path.abspath(".")
        self.metadir_name = '.baboon'

        self.init_config()

    def init_config(self):
        """ Initializes:
        - the argument parser
        - the baboon configuration file
        - the watched project configuration file

        and puts all configurations in the config dict
        """
        self._init_config_arg()
        self._init_config_file()
        if self.init is False:
            self.check_config()  # checks the configuration, should be ok
            self._init_config_project()

    def check_config(self, safe=False):
        """ Checks the configuration state
        """
        path = os.path.join(self.path, self.metadir_name)
        ret = os.path.isdir(path)

        if ret or safe:
            return ret
        else:
            msg = """%s seems to be not a directory. \
Verify that 'baboon init' was called in the directory before.""" % path
            raise BaboonException(msg)

        # TODO: checks if server_host, jid and password is valid

    def _get_config_path(self):
        """ Gets the configuration path with the priority order :
        1) config command line argument
        2) <project_path>/conf/baboonrc
        3) ~/.baboonrc
        4) /etc/baboon/baboonrc
        5) environment variable : BABOONRC

        elsewhere : return None
        """
        if self.configpath is not None:
            return self.configpath

        config_name = 'baboonrc'

        etc_path = '/etc/baboonrc/%s' % config_name
        user_path = '%s/.%s' % (os.path.expanduser('~'), config_name)
        curdir_path = '%s/conf/%s' % (os.curdir, config_name)

        for loc in etc_path, user_path, curdir_path:
            if os.path.isfile(loc):
                return loc

        # if there's no good path, use the global environment
        # elsewhere, return None
        return os.environ.get("BABOONRC")

    def _init_config_arg(self):
        arg_parser = ArgumentParser()
        try:
            args = arg_parser.args
            self.path = args.path or self.path
            self.path = os.path.abspath(self.path)
            self.metadir = os.path.join(self.path, self.metadir_name)
            self.metadir_watched = os.path.join(self.metadir, 'watched')
            self.init = args.init is True
            self.configpath = args.config

        except AttributeError:
            sys.stderr.write("Failed to parse arguments\n")
            exit(1)

    def _init_config_file(self):
        filename = self._get_config_path()
        parser = RawConfigParser()
        parser.read(filename)

        for section in parser.sections():
            for item in parser.items(section):
                if not hasattr(self, item[0]):
                    setattr(self, item[0], item[1])

    def _init_config_project(self):
        # TODO: the config project must support the ConfigParser format ?
        if not self.init:
            try:
                filename = os.path.join(self.metadir, 'config')
                with open(filename, 'r') as f:
                    lines = f.readlines()
                    for line in lines:
                        try:
                            splitted = line.split('=')
                            setattr(self, splitted[0].strip(),
                                    splitted[1].strip())
                        except:
                            err = 'Cannot parse the project config file'
                            raise BaboonException(err)
            except:
                err = 'Cannot find a baboonrc in the project to watch'
                raise BaboonException(err)
