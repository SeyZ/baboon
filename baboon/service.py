import os

from base64 import b64encode, b64decode
from zlib import compress, decompress
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

        # Key: author + filepath
        # Value: True if the last message received by the author was a
        # conflict
        self.in_conflict = {}

        self.xmpp = Transport(self._handle_event)
        self.xmpp.register_plugin('xep_0060')  # PubSub

        # Initialize the scm class to use
        scm_classes = Diffman.__subclasses__()
        for cls in scm_classes:
            tmp_inst = cls()
            if tmp_inst.scm_name == self.config.scm:
                self.diffman = tmp_inst

    def start(self):
        self.logger.debug("Connecting to XMPP...")
        if self.xmpp.connect():
            self.logger.debug("Connected to XMPP")
            self.xmpp.process()
        else:
            self.logger.error("Unable to connect.")

    def close(self):
        self.logger.debug("Closing the XMPP connection...")
        self.xmpp.close()

    def broadcast(self, filepath):
        thediff = self.make_patch(filepath)

        # compress the diff
        thediff = compress(thediff, 9)

        # base64 the diff
        thediff = b64encode(thediff)

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
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            for item in msg['pubsub_event']['items']['substanzas']:
                try:
                    payload = item['payload']
                    filepath = payload[0].text
                    thediff = payload[1].text
                    thediff = b64decode(thediff)
                    thediff = decompress(thediff)
                    author = payload[2].text

                    if author != self.config.jid:
                        result = self.apply_patch(thediff, filepath)
                        if not result:
                            self.in_conflict[author + filepath] = True
                            msg = "Conflict detected with %s in %s" % \
                                (author, filepath)
                            self.logger.info(msg)
                            self.logger.debug("With the diff:\n%s" % thediff)
                            self.notify(msg)
                        else:
                            if self.in_conflict.get(author + filepath):
                                msg = "Conflict resolved with %s in %s" % \
                                    (author, filepath)
                                self.in_conflict[author + filepath] = False
                                self.logger.info(msg)
                                self.notify(msg)
                            else:
                                msg = "Everything seems to be perfect with" \
                                    " %s in %s" % (author, filepath)
                                self.logger.debug(msg)
                except:
                    pass

        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])

    def notify(self, msg):
        self.xmpp.sendMessage(self.config.jid, msg)
