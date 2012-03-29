import sleekxmpp

from sleekxmpp.xmlstream import ET
from logger import logger
from config import Config


@logger
class Transport(sleekxmpp.ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self, service):
        """
        """

        self.config = Config()
        self.logger.debug("Loaded baboon configuration")

        # Store the service class
        self.service = service

        sleekxmpp.ClientXMPP.__init__(self, self.config.jid,
                                      self.config.password)
        self.logger.debug("Configured SleekXMPP library")

        # Register plugins
        self.register_plugin('xep_0060')  # PubSub

        self.add_event_handler("session_start", self.start)
        self.logger.debug("Listening 'session_start' sleekxmpp event")

        self.add_event_handler("message", self.message)
        self.logger.debug("Listening 'message' sleekxmpp event")

        self.register_handler(
            sleekxmpp.xmlstream.handler.Callback(
                'Pubsub event',
                sleekxmpp.xmlstream.matcher.StanzaPath(
                    'message/pubsub_event'),
                self._handle_event))
        self.logger.debug("Listening 'message/pubsub_event' sleekxmpp event")

    def open(self):
        self.logger.debug("Connecting to XMPP...")
        if self.connect():
            self.logger.debug("Connected to XMPP")
            self.process()
        else:
            self.logger.error("Unable to connect.")

    def start(self, event):
        """ Handler for the session_start sleekxmpp event
        """
        self.send_presence()
        self.get_roster()

        # register the pubsub plugin
        self.pubsub = self.plugin["xep_0060"]

        self.logger.info('Connected')
        self.retreive_messages()

    def retreive_messages(self):
        result = self.pubsub.get_item(self.config.server_host,
                                      self.config.node_name,
                                      '')
        items = result['pubsub']['items']['substanzas']
        self.logger.info('Retreived %s items' % len(items))

    def _handle_event(self, msg):
        if msg['type'] in ('normal', 'headline'):
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])
            items = msg['pubsub_event']['items']['substanzas']
            self.service.verify_msg(items)
        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])

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
