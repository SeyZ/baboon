import os
import sys

from config import config
from notifier import Notifier
from initialize import Initializor
from errors.baboon_exception import BaboonException


class Main(object):
   def __init__(self):
      if config.init:
         try:
            init = Initializor()
            init.create_metadir()
            init.create_config_file()
            init.walk_and_copy()
         except BaboonException, e:
            sys.stderr.write(str(e) + '\n')
      else:
         try:
            config.check_config()
         except BaboonException, e:
            sys.stderr.write(str(e) + '\n')
            exit(1)

         notifier = Notifier()
         notifier.watch()
