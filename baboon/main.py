import sys
import signal

from plugins import *
from config import config
from commands import commands
from transport import WatchTransport
from monitor import Monitor
from common.logger import logger
from common.errors.baboon_exception import BaboonException


@logger
class Main(object):

    def __init__(self):
        self.monitor = None

        # The start command is a special command. Call it from this class
        if config['which'] == 'start':
            self.start()
            return

        # Call the correct method according to the current arg subparser.
        if hasattr(commands, config['which']):
            getattr(commands, config['which'])()

    def start(self):
        try:
            # exists baboon when receiving a sigint signal
            signal.signal(signal.SIGINT, self.sigint_handler)

            self.transport = WatchTransport()
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
