import sys
import signal

from plugins import *
from logger import logger
from config import Config
from errors.baboon_exception import BaboonException
from transport import Transport
from monitor import Monitor


@logger
class Main(object):
    def __init__(self):
        self.monitor = None

        try:
            # instanciates the config
            self.config = Config()

            # exists baboon when receiving a sigint signal
            signal.signal(signal.SIGINT, self.sigint_handler)

            self.transport = Transport()
            self.transport.open()

            self.monitor = Monitor(self.transport)
            self.monitor.watch()

            # TODO this won't work on windows...
            signal.pause()

        except BaboonException, err:
            sys.stderr.write("%s\n" % err)
            # Try to close the transport properly. If the transport is
            # not correctly started, the close() method has no effect.
            self.transport.close()

            # Same thing for the monitor
            if self.monitor:
                self.monitor.close()

            # Exits with a fail return code
            sys.exit(1)

    def sigint_handler(self, signal, frame):
        """ Handler method for the SIGINT signal.
        XMPP connection and service monitoring are correctly closed.
        Closing baboon in a clean way.
        """
        self.logger.debug("Received SIGINT signal")
        self.transport.close()
        self.monitor.close()

        self.logger.info("Bye !")
        sys.exit(0)
