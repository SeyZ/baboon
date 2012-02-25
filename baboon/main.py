import sys
import logging

from config import config
from monitor import Monitor
from initialize import Initializor
from service import Service
from errors.baboon_exception import BaboonException


class Main(object):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)-8s %(message)s')
        try:
            if config.init:
                self.default_initializor()
            else:
                self.check_config()

                self.service = Service()
                self.service.start()

                self.monitor = Monitor(self.service)
                self.monitor.watch()
        except BaboonException as err:
            sys.stderr.write(err)

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
