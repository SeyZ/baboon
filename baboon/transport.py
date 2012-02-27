import sys
import sleekxmpp
import logging

from logger import logger
from config import Config
from sleekxmpp.xmlstream import ET


@logger
class Transport(sleekxmpp.ClientXMPP):
    """
    """

    def __init__(self, handle_event):
        self.config = Config()

        sleekxmpp.ClientXMPP.__init__(self, self.config.jid,
                                      self.config.password)

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

        self.logger.info('XMPP initialization done')

    def broadcast(self, filepath, diff):
        """ Broadcasts the diff to the pubsub xmpp node
        @param filepath: the relative (project) file path
        @type filepath: str
        """
        stanza = """
<patch>
  <project>%s</project>
  <file>%s</file>
  <diff>%s</diff>
  <author>%s</author>
</patch>""" % (self.config.project_name, filepath, diff, self.config.jid)

        payload = ET.fromstring(stanza)
        try:
            result = self.pubsub.publish(self.config.server_host,
                                         self.config.node_name,
                                         payload=payload)
            id = result['pubsub']['publish']['item']['id']
            self.logger.info('Published at item id: %s' % id)
        except:
            self.logger.error('Could not publish to: %s' %
                              self.config.node_name)

    def message(self, msg):
        """ Processes incoming message stanzas. Also includes MUC messages and
        error messages.
        """
        if msg['type'] in ('chat', 'normal'):
            self.logger.info("Received the message %(body)s:" % msg)
