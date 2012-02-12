import os
import argparse
import sys

from errors.baboon_exception import BaboonException


class ArgumentParser(object):
    def __init__(self):
      parser = argparse.ArgumentParser(description='Baboon ! Ook !')
      parser.add_argument('--path', metavar='path',
                          help='Specify the path you want to monitor')
      parser.add_argument('init', metavar='init', nargs='?', default=False,
                          type=bool, help='Initialize the baboon metadata')

      self.args = parser.parse_args()


class Config(object):
    def __init__(self):
        # Configures the default path
        self.path = os.path.abspath(".")

        self.init_config()

    def init_config(self):
        arg_parser = ArgumentParser()
        try:
            args = arg_parser.args
            self.path = arg_parser.args.path or self.path
            self.init = arg_parser.args.init is True
        except AttributeError:
            sys.stderr.write("Failed to parse arguments\n")
            exit(1)

    def check_config(self, safe=False):
        path = os.path.join(self.path, ".baboon")
        ret = os.path.isdir(path)

        if ret or safe:
            return ret
        else:
            msg = """%s seems to be not a directory. \
Verify that 'baboon init' was called in the directory before.""" % path
            raise BaboonException(msg)

config = Config()
