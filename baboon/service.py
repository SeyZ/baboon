import logging

from transport import Transport
from diffman import Diffman


class Service(object):
    def __init__(self):
        """
        """

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        self.xmpp = Transport()
        self.xmpp.register_plugin('xep_0030')  # Service Discovery
        self.xmpp.register_plugin('xep_0004')  # Data Forms
        self.xmpp.register_plugin('xep_0060')  # PubSub
        self.xmpp.register_plugin('xep_0199')  # XMPP Ping

        self.diffman = Diffman()

    def start(self):
        if self.xmpp.connect():
            self.xmpp.process()
        else:
            print("Unable to connect.")

    def broadcast(self, patch):
        self.xmpp.broadcast(patch)

    def make_patch(self, oldfile, newfile):
        """ Creates a patch between oldfile and newfile
        """
        patch = self.diffman.diff(oldfile, newfile)
        self.logger.debug("Created the patch: %s" % patch)
        return patch

    def apply_patch(self, thepatch, thefile):
        """ Applies the patch on the file 'thefile'.
        Returns True if success
        """

        return not False in self.diffman.patch(thepatch, thefile)[1]
