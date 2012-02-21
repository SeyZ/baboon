import logging
import sleekxmpp

from sleekxmpp.xmlstream import ET


class Transport(sleekxmpp.ClientXMPP):

    """
    A simple SleekXMPP bot that will echo messages it
    receives, along with a short thank you message.
    """

    def __init__(self, jid, password):
        sleekxmpp.ClientXMPP.__init__(self, jid, password)

        self.add_event_handler("session_start", self.start)
        self.add_event_handler("message", self.message)
        self.register_handler(
            sleekxmpp.xmlstream.handler.Callback(
                'Pubsub event',
                sleekxmpp.xmlstream.matcher.StanzaPath(
                    'message/pubsub_event'),
                self._handle_event))

    def _handle_event(self, msg):
        print('Received pubsub event: %s' % msg['pubsub_event'])

    def start(self, event):
        """ Processes the session_start event.
        """
        self.send_presence()
        self.get_roster()
        self.pubsub = self.plugin["xep_0060"]
        self.broadcast('test')

    def broadcast(self, msg):
        payload = ET.fromstring("<test xmlns='test'>%s</test>" % msg)
        try:
            result = self.pubsub.publish('pubsub.localhost', 'node1',
                                         payload=payload)
            id = result['pubsub']['publish']['item']['id']
            print('Published at item id: %s' % id)
        except:
            logging.error('Could not publish to: %s' % 'node1')

    def message(self, msg):
        """ Processes incoming message stanzas. Also includes MUC messages and
        error messages.
        """
        if msg['type'] in ('chat', 'normal'):
            msg.reply("Thanks for sending\n%(body)s" % msg).send()
