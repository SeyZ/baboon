import os

from logger import logger
from config import Config
from transport import Transport
from diffman import Diffman


@logger
class Service(object):
    def __init__(self):
        """
        """
        self.config = Config()

        self.xmpp = Transport(self._handle_event)
        self.xmpp.register_plugin('xep_0030')  # Service Discovery
        self.xmpp.register_plugin('xep_0004')  # Data Forms
        self.xmpp.register_plugin('xep_0060')  # PubSub
        self.xmpp.register_plugin('xep_0199')  # XMPP Ping

        self.diffman = Diffman()

    def start(self):
        self.logger.info("Connecting to XMPP...")
        if self.xmpp.connect():
            self.logger.info("Connected to XMPP")
            self.xmpp.process()
        else:
            self.logger.error("Unable to connect.")

    def close(self):
        self.logger.info("Closing the XMPP connection...")
        self.xmpp.close()

    def broadcast(self, filepath):
        thediff = self.make_patch(filepath)
        self.xmpp.broadcast(filepath, thediff)

    def make_patch(self, filepath):
        """ Creates a patch of the filepath
        """
        patch = self.diffman.diff(filepath)
        self.logger.debug("Created the patch: %s" % patch)
        return patch

    def apply_patch(self, thepatch, thefile):
        """ Applies the patch on the file 'thefile'.
        Returns True if success
        """
        return self.diffman.patch(thepatch, "%s" % os.path.join(
                self.config.path, thefile))

    def _handle_event(self, msg):
        if msg['type'] == 'headline':
            self.logger.info("Received pubsub item(s)")
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            for item in msg['pubsub_event']['items']['substanzas']:
                try:
                    payload = item['payload']
                    filepath = payload[0].text
                    thediff = payload[1].text
                    author = payload[2].text

                    if author != self.config.jid:
                        result = self.apply_patch(thediff, filepath)
                        if not result:
                            msg = "Conflict detected"
                            self.logger.info(msg)
                            self.notify(msg)
                        else:
                            msg = "Everything seems to be perfect"
                            self.logger.info(msg)
                            self.notify(msg)
                except:
                    pass

        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])

    def notify(self, msg):
        self.xmpp.sendMessage(self.config.jid, msg)
