import sleekxmpp
import executor

from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath

from config import config
from common.stanza.rsync import RsyncOk, RsyncFinished, MergeStatus
from common.logger import logger


@logger
class Transport(sleekxmpp.ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self):
        sleekxmpp.ClientXMPP.__init__(self,
                                      'admin@baboon-project.org/baboond',
                                      'secret')
        self.register_plugin('xep_0060')  # PubSub

        self.add_event_handler('session_start', self.start)

        self.register_handler(Callback(
                'RsyncStart Handler',
                StanzaPath('iq@type=set/rsync_start'),
                self._handle_rsync_start))

        self.register_handler(Callback(
                'RsyncStop Handler',
                StanzaPath('iq@type=set/rsync_stop'),
                self._handle_rsync_stop))

        if self.connect():
            self.process()

    def _handle_rsync_start(self, iq):
        # TODO - Deal with errors

        ok_msg = RsyncOk()
        ok_msg.values = executor.preparator.prepare_rsync_start()
        iq.reply().setPayload(ok_msg).send()

    def _handle_rsync_stop(self, iq):
        # TODO - Deal with errors

        ok_msg = RsyncFinished()
        executor.preparator.prepare_rsync_stop(
            iq['rsync_stop'].values['req_id'])
        iq.reply().setPayload(ok_msg).send()

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        # register the pubsub plugin
        self.pubsub = self.plugin['xep_0060']

    def alert(self, msg):
        """ Broadcast the msg on the pubsub node (written in the
        config file).
        """

        status_msg = MergeStatus()
        status_msg['node'] = config.node
        status_msg['status'] = msg

        try:
            result = self.pubsub.publish(config.pubsub,
                                         config.node,
                                         payload=status_msg)
            id = result['pubsub']['publish']['item']['id']
            self.logger.debug('Published at item id: %s' % id)
        except:
            self.logger.debug('Could not publish to: %s' %
                              'Baboon')

    def close(self):
        self.disconnect()


transport = Transport()
2
