from baboon.common.eventbus import eventbus
from baboon.common.utils import exec_cmd
from baboon.common.logger import logger


@logger
class Notifier(object):
    """ This class listens on the event bus and run notification command from
    the configuration file when a notification is sent.
    """

    def __init__(self, notif_cmd):

        self.notif_cmd = notif_cmd
        eventbus.register('conflict-result', self._on_message)

        self.logger.debug("Notifier loaded with command: %s" % self.notif_cmd)

    def _on_message(self, message):

        exec_cmd(self.notif_cmd %(message))
