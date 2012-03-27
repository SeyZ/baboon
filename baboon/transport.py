import sleekxmpp

from logger import logger
from config import Config
from sleekxmpp.xmlstream import ET


@logger
class Transport(sleekxmpp.ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self, handle_event):
        """ @param handle_event: this method will be called when a
        message is received via XMPP.
        @type handle_event: method.
        """

        self.config = Config()
        self.logger.debug("Loaded baboon configuration")

        sleekxmpp.ClientXMPP.__init__(self, self.config.jid,
                                      self.config.password)
        self.logger.debug("Configured SleekXMPP library")

        self.add_event_handler("session_start", self.start)
        self.logger.debug("Listening 'session_start' sleekxmpp event")

        self.add_event_handler("message", self.message)
        self.logger.debug("Listening 'message' sleekxmpp event")

        self.register_handler(
            sleekxmpp.xmlstream.handler.Callback(
                'Pubsub event',
                sleekxmpp.xmlstream.matcher.StanzaPath(
                    'message/pubsub_event'),
                handle_event))
        self.logger.debug("Listening 'message/pubsub_event' sleekxmpp event")

    def start(self, event):
        """ Handler for the session_start sleekxmpp event
        """
        self.send_presence()
        self.get_roster()

        # register the pubsub plugin
        self.pubsub = self.plugin["xep_0060"]

        self.logger.info('Connected')

    def close(self):
        self.disconnect()
        self.logger.debug('Closed the XMPP connection')

    def broadcast(self, filepath, diff):
        """ Broadcasts the diff to the pubsub xmpp node @param
        filepath: the relative (project) file path @type filepath: str
        """
        stanza = """
<patch>
  <file>%s</file>
  <diff>%s</diff>
  <author>%s</author>
</patch>""" % (filepath, diff, self.config.jid)

        payload = ET.fromstring(stanza)
        try:
            result = self.pubsub.publish(self.config.server_host,
                                         self.config.node_name,
                                         payload=payload)
            id = result['pubsub']['publish']['item']['id']
            self.logger.debug('Published at item id: %s' % id)
        except:
            self.logger.error('Could not publish to: %s' %
                              self.config.node_name)

    def message(self, msg):
        """ Processes incoming message stanzas. Also includes MUC messages and
        error messages.
        """
        if msg['type'] in ('chat', 'normal'):
            self.logger.debug("Received the message %(body)s:" % msg)
