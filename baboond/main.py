import signal

from executor import Scheduler, tasks
from task import EndTask
from common.logger import logger


@logger
class Main(object):

    def __init__(self):
        """ Initializes baboonsrv
        """

        signal.signal(signal.SIGINT, self.signal_handler)

        e = Scheduler()
        e.start()

        signal.pause()
        e.join()

    def signal_handler(self, signal, frame):
        tasks.put(EndTask())
