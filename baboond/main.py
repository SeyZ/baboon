import sys
import signal

from executor import Scheduler, tasks
from task import EndTask


e = Scheduler()


def main():
    """ Initializes baboonsrv
    """

    signal.signal(signal.SIGINT, signal_handler)
    e.start()
    signal.pause()


def signal_handler(signal, frame):
    tasks.put(EndTask())
    e.join()
