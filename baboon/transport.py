import logging
import sleekxmpp

from config import config
from diffman import Diffman
from sleekxmpp.xmlstream import ET


class Transport(sleekxmpp.ClientXMPP):
    """
    """

    def __init__(self):
        sleekxmpp.ClientXMPP.__init__(self, config.jid, config.password)

        # configures logger
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

        # sets xmpp handlers
        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.register_handler(
            sleekxmpp.xmlstream.handler.Callback(
                'Pubsub event',
                sleekxmpp.xmlstream.matcher.StanzaPath(
                    'message/pubsub_event'),
                self._handle_event))

    def _handle_event(self, msg):
        if msg['type'] == 'headline':
            self.logger.info("Received pubsub item(s)")
            self.logger.debug("Received pubsub item(s) : %s" %
                              msg['pubsub_event'])

            differ = Diffman()
            for item in msg['pubsub_event']['items']['substanzas']:
                payload = item['payload'].text
                differ.patch(payload)
        else:
            self.logger.debug("Received pubsub event: %s" %
                              msg['pubsub_event'])

    def start(self, event):
        """ Processes the session_start event.
        """
        self.send_presence()
        self.get_roster()
        self.pubsub = self.plugin["xep_0060"]

    def broadcast(self, diff):
        payload = ET.fromstring("<diff>%s</diff>" % diff)
        try:
            result = self.pubsub.publish(config.server_host, config.node_name,
                                         payload=payload)
            id = result['pubsub']['publish']['item']['id']
            print('Published at item id: %s' % id)
        except:
            logging.error('Could not publish to: %s' % config.node_name)

    def message(self, msg):
        """ Processes incoming message stanzas. Also includes MUC messages and
        error messages.
        """
        if msg['type'] in ('chat', 'normal'):
            msg.reply("Thanks for sending\n%(body)s" % msg).send()
