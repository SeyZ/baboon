import os
import sys
import argparse
import logging

from errors.baboon_exception import BaboonException


class ArgumentParser(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Baboon ! Ook !')
        parser.add_argument('--path', metavar='path',
                          help='Specify the path you want to monitor')
        parser.add_argument('init', metavar='init', nargs='?', default=False,
                            type=bool, help='Initialize the baboon metadata')

        parser.add_argument('-q', '--quiet', help='set logging to ERROR',
                          action='store_const', dest='loglevel',
                          const=logging.ERROR, default=logging.INFO)

        parser.add_argument('-d', '--debug', help='set logging to DEBUG',
                          action='store_const', dest='loglevel',
                          const=logging.DEBUG, default=logging.INFO)

        parser.add_argument('-v', '--verbose', help='set logging to COMM',
                          action='store_const', dest='loglevel',
                          const=5, default=logging.INFO)

        self.args = parser.parse_args()

        logging.basicConfig(level='INFO',
                            format='%(levelname)-8s %(message)s')


class Config(object):
    def __init__(self):
        # Configures the default path
        self.path = os.path.abspath(".")
        self.metadir_name = '.baboon'

        self.init_config()

    def init_config(self):
        arg_parser = ArgumentParser()
        try:
            args = arg_parser.args
            self.path = args.path or self.path
            self.path = os.path.abspath(self.path)
            self.metadir = "%s%s%s" % (self.path, os.sep, self.metadir_name)
            self.metadir_watched = "%s%s%s" % (self.metadir, os.sep, 'watched')
            self.init = args.init is True
        except AttributeError:
            sys.stderr.write("Failed to parse arguments\n")
            exit(1)

    def check_config(self, safe=False):
        path = os.path.join(self.path, self.metadir_name)
        ret = os.path.isdir(path)

        if ret or safe:
            return ret
        else:
            msg = """%s seems to be not a directory. \
Verify that 'baboon init' was called in the directory before.""" % path
            raise BaboonException(msg)

config = Config()
