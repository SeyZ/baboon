import signal

from baboond.transport import transport
from baboond.dispatcher import dispatcher
from common.logger import logger

@logger
class Main(object):

    def __init__(self):
        """ Initializes baboond.
        """

        signal.signal(signal.SIGINT, self.signal_handler)
        signal.pause()

    def signal_handler(self, signal, frame):
        dispatcher.close()
        transport.close()
