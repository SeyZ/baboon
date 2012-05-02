import sys
import signal

from bottle import run
from executor import Executor, tasks
from routes import *
from task import EndTask


e = Executor()


def main():
    """ Initializes baboonsrv
    """

    signal.signal(signal.SIGINT, signal_handler)

    e.start()

    run(host='localhost', port=8080)

    signal.pause()


def signal_handler(signal, frame):
    print 'Bye !'
    tasks.put(EndTask())
    e.join()
    sys.exit(0)
