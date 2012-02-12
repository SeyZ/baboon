import os

import argparse

from config import config
from notifier import Notifier
from initialize import Initializor


class ArgumentParser(object):
   def __init__(self):
      parser = argparse.ArgumentParser(description='Baboon ! Ook !')
      parser.add_argument('--path', metavar='path',
                          help='Specify the path you want to monitor')
      parser.add_argument('init', metavar='init', nargs='?',
                          help='Initialize the baboon metadata')

      self.args = parser.parse_args()


class Main(object):
   def __init__(self):
      arg_parser = ArgumentParser()
      if arg_parser.args.path:
          config.path = arg_parser.args.path

      if arg_parser.args.init:
         Initializor()
      else:
         check = config.check_config()
         if not check:
            print "%s seems to be not correctly initialized.\nYou should" \
                " verify 'baboon init' was called in the directory." % config.path
            exit(1)

         notifier = Notifier()
         notifier.watch()
