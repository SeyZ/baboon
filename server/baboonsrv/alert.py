import sleekxmpp

from sleekxmpp.xmlstream import ET
from config import Config


class Xmpp(sleekxmpp.ClientXMPP):
    """ A xmpp client with the support of xep 0060.
    """

    def __init__(self):
        """ Initialize the pubsub client.
        """

        # Get the config in order to have pubsub server, jid and
        # passwd.
        self.config = Config()

        # Initialize sleekxmpp
        sleekxmpp.ClientXMPP.__init__(self, self.config.jid,
                                      self.config.password)

        # Register plugins
        self.register_plugin('xep_0060')  # PubSub

        # Register events
        self.add_event_handler("session_start", self.start)

        # Connect
        if self.connect():
            self.process()

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        # register the pubsub plugin
        self.pubsub = self.plugin["xep_0060"]

    def alert(self, msg):
        """ Broadcast the msg on the pubsub node (written in the
        config file).
        """

        xml_element = ET.fromstring('<status>%s</status>' % msg)

        try:
            result = self.pubsub.publish(self.config.pubsub,
                                         self.config.node,
                                         payload=xml_element)
            id = result['pubsub']['publish']['item']['id']
            print('Published at item id: %s' % id)
        except:
            print('Could not publish to: %s' %
                  'Baboon')
