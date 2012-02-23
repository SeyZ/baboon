import logging
import sleekxmpp

from config import config
from sleekxmpp.xmlstream import ET


class Transport(sleekxmpp.ClientXMPP):
    """
    """

    def __init__(self, handle_event):
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
                handle_event))

    def start(self, event):
        """ Processes the session_start event.
        """
        self.send_presence()
        self.get_roster()
        self.pubsub = self.plugin["xep_0060"]

    def broadcast(self, filepath, diff):
        """ Broadcasts the diff to the pubsub xmpp node
        @param filepath: the relative (project) file path
        @type filepath: str
        """
        stanza = "<patch><file>%s</file><diff>%s</diff></patch>" \
            % (filepath, diff)
        payload = ET.fromstring(stanza)
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
