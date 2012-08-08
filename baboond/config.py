import argparse
import logging
import logging.config

from common.config import Config
from logconf import LOGGING


class ArgumentParser(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Baboon ! Ook !')

        # logging args
        parser.add_argument('-d', '--debug', help='set logging to DEBUG',
                            action='store_const',
                            dest='loglevel',
                            const=logging.DEBUG,
                            default=logging.INFO)

        self.args = parser.parse_args()

config = Config(ArgumentParser(), LOGGING, 'baboondrc').attrs
