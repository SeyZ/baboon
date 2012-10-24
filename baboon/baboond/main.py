from baboon.baboond.transport import transport
from baboon.baboond.dispatcher import dispatcher
from baboon.common.eventbus import eventbus


def main():
    """ Initializes baboond.
    """

    try:
        while not transport.disconnected.is_set():
            transport.disconnected.wait(5)
    except KeyboardInterrupt:
        dispatcher.close()
        transport.close()
