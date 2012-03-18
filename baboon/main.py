import sys
import signal

from logger import logger
from config import Config
from monitor import Monitor
from service import Service
from errors.baboon_exception import BaboonException


@logger
class Main(object):
    def __init__(self):
        try:
            # instanciates the config
            self.config = Config()

            # exists baboon when receiving a sigint signal
            signal.signal(signal.SIGINT, self.sigint_handler)

            # load plugins
            from plugins import *

            self.service = Service()
            self.service.start()

            self.monitor = Monitor(self.service)
            self.monitor.watch()

            signal.pause()
        except BaboonException, err:
            sys.stderr.write("%s\n" % err)

    def sigint_handler(self, signal, frame):
        """ Handler method for the SIGINT signal.
        XMPP connection and service monitoring are correctly closed.
        Closing baboon in a clean way.
        """
        self.logger.debug("Received SIGINT signal")
        self.monitor.close()
        self.service.close()

        self.logger.info("Bye !")
        sys.exit(0)
