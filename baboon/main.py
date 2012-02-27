import sys
import logging

from utils import logger
from config import Config
from monitor import Monitor
from initialize import Initializor
from service import Service
from errors.baboon_exception import BaboonException


@logger
class Main(object):
    def __init__(self):
        logging.basicConfig(level=logging.DEBUG,
                            format='%(levelname)-8s (%(name)s) %(message)s')

        try:
            # instanciates the config (singleton with borg pattern)
            self.config = Config()

            if self.config.init:
                self.default_initializor()
            else:
                self.check_config()

                self.service = Service()
                self.service.start()

                self.monitor = Monitor(self.service)
                self.monitor.watch()
        except BaboonException, err:
            sys.stderr.write("%s\n" % err)

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
            self.config.check_config()
        except BaboonException, e:
            sys.stderr.write(str(e) + '\n')
            exit(1)
