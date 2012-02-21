import sys
import logging

from config import config
from notifier import Notifier
from initialize import Initializor
from service import service
from errors.baboon_exception import BaboonException


class Main(object):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)-8s %(message)s')
        if config.init:
            self.default_initializor()
        else:
            self.check_config()
            self.watch()
            service.start()

    def default_initializor(self):
        try:
            init = Initializor()
            init.create_metadir()
            init.create_config_file()
            init.walk_and_copy()
        except BaboonException, e:
            sys.stderr.write(str(e) + '\n')

    def check_config(self):
        try:
            config.check_config()
        except BaboonException, e:
            sys.stderr.write(str(e) + '\n')
            exit(1)

    def watch(self):
        notifier = Notifier()
        notifier.watch()
