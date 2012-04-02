import sleekxmpp

from sleekxmpp.xmlstream import ET
from logger import logger
from config import Config


@logger
class Transport(sleekxmpp.ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self, mediator):
        """
        """

        self.config = Config()
        self.logger.debug("Loaded baboon configuration")

        # Store the mediator class
        self.mediator = mediator

        sleekxmpp.ClientXMPP.__init__(self, self.config.jid,
                                      self.config.password)
        self.logger.debug("Configured SleekXMPP library")

        # Register plugins
        self.register_plugin('xep_0060')  # PubSub

        # Register events
        self.add_event_handler("session_start", self.start)
        self.logger.debug("Listening 'session_start' sleekxmpp event")

        self.add_event_handler("message", self.message)
        self.logger.debug("Listening 'message' sleekxmpp event")

        self.register_handler(
            sleekxmpp.xmlstream.handler.Callback(
                'Pubsub event',
                sleekxmpp.xmlstream.matcher.StanzaPath(
                    'message/pubsub_event'),
                self._pubsub_event))
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

    def close(self):
        self.disconnect()
        self.logger.debug('Closed the XMPP connection')

    def broadcast(self, payload):
        """ Broadcasts via XMPP the payload. The payload can be a list
        of Item or a single item.
        """

        # Transforms all Item objects to a single XML string
        xmls = ""
        if isinstance(payload, dict):
            xmls = payload.to_xml()
        elif isinstance(payload, list):
            for elem in payload:
                xmls += elem.to_xml()

        # Transforms the XML string to a valid sleekxmpp XML element
        xml_element = ET.fromstring(xmls)

        try:
            result = self.pubsub.publish(self.config.server_host,
                                         self.config.node_name,
                                         payload=xml_element)
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

    def _pubsub_event(self, msg):
        if msg['type'] in ('normal', 'headline'):
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            # Gets the sleekxmpp stanzas
            items = msg['pubsub_event']['items']['substanzas']

            # Transforms a list of sleekxmpp stanzas to a list of
            # dicts
            payloads = [Item(self._transform(x['payload'])) for x in items]

            # Verifies if there's a conflict in the payloads
            self.mediator.verify_msg(payloads)
        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])

    def _transform(self, xmpp_payload):
        """ Transforms a XmppEventItem to a human readable dict
        """
        return {
            'filepath': xmpp_payload[0].text,
            'diff': xmpp_payload[1].text,
            'author': xmpp_payload[2].text,
            }


class Item(dict):
    """ Represents all information needed by a diff :
    - file path
    - author of the diff
    - diff
    """

    TEMPLATE = """
<patch>
  <file>{0}</file>
  <diff>{1}</diff>
  <author>{2}</author>
</patch>"""

    def __init__(self, payload, *args):
        """ Registers the useful information from the payload dict to
        the item dict
        """

        dict.__init__(self, args)
        self.__setitem__('filepath', payload['filepath'])
        self.__setitem__('author', payload['author'])
        self.__setitem__('diff', payload['diff'])

    def to_xml(self):
        return self.TEMPLATE.format(self['filepath'],
                                    self['diff'],
                                    self['author'])
