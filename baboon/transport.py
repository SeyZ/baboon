import os
import pickle
import struct

from sleekxmpp import ClientXMPP
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.exceptions import IqError
from sleekxmpp.plugins.xep_0060.stanza.pubsub_event import EventItem

from config import config
from common.logger import logger
from common import pyrsync
from common.stanza import rsync


@logger
class Transport(ClientXMPP):
    """ The transport has the responsability to communicate via HTTP
    with the baboon server and to subscribe with XMPP 0060 with the
    Baboon XMPP server.
    """

    def __init__(self, config):
        """ Transport initializes all SleekXMPP stuff like plugins,
        events and more.
        """

        self.config = config
        self.logger.debug("Loaded baboon configuration")

        ClientXMPP.__init__(self, config.jid, config.password)
        self.logger.debug("Configured SleekXMPP library")

        # Register plugins
        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0065')  # Socks5 Bytestreams

        # Register events
        self.add_event_handler('socks_recv', self.on_recv)
        self.add_event_handler('session_start', self.start)

        self.register_handler(Callback('Pubsub event', StanzaPath(
                    'message/pubsub_event'), self._pubsub_event))
        self.logger.debug("Listening 'message/pubsub_event' sleekxmpp event")

    def open(self):
        """ Connects to the XMPP server.
        """

        self.logger.debug("Connecting to XMPP...")
        if self.connect():
            self.logger.debug("Connected to XMPP")
            self.process()
        else:
            self.logger.error("Unable to connect.")

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        # Registers xep plugins
        self.pubsub = self.plugin["xep_0060"]
        self.streamer = self.plugin["xep_0065"]

        # Negotiates the bytestream
        streamhost_used = self.streamer.handshake(config.server,
                                                  config.streamer)

        # Registers the SID to retrieve later to send/recv data to the
        # good socket stored in self.streamer.proxy_threads dict.
        self.sid = streamhost_used['socks']['sid']

        self.logger.info('Connected')

    def close(self):
        """ Closes the XMPP connection.
        """

        self.streamer.close()
        self.disconnect()
        self.logger.debug('Closed the XMPP connection')

    def rsync(self, files):
        """ Starts a rsync transaction, rsync and stop the
        transaction.

        Raises a BaboonException if there's a problem.
        """

        iq = self.Iq(sto=config.server, stype='set')

        iq['rsync']['sid'] = self.sid
        iq['rsync']['node'] = 'synapse'
        iq['rsync']['files'] = files

        try:
            iq.send()
        except IqError, e:
            self.logger.error(e.iq)

    def on_recv(self, payload):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        deltas = []  # The list of delta.

        # Sets the future socket response dict.
        ret = {'from': self.boundjid.bare,
               'node': self.config.node,
               }

        # Unpacks the recv data.
        recv = payload['data']
        data = self._unpack(recv)

        # Gets the list of hashes.
        all_hashes = data['hashes']

        for elem in all_hashes:
            # 'elem' is a tuple. The first element is the relative
            # path to the current file. The second is the server-side
            # hashes associated to this path.
            relpath = elem[0]
            hashes = elem[1]

            fullpath = os.path.join(self.config.path, relpath)
            if os.path.exists(fullpath):
                # Computes the local delta of the current file.
                patchedfile = open(fullpath, 'rb')
                delta = pyrsync.rsyncdelta(patchedfile, hashes)
                delta = (relpath, delta)

                # Appends the result to the list of delta.
                deltas.append(delta)
            else:
                # TODO: Handle this error ?
                pass

        # Adds the list of deltas in the response dict.
        ret['delta'] = deltas

        # Sends the result over the socket.
        self.streamer.send(self.sid, self._pack(ret))

    def _pack(self, data):
        data = pickle.dumps(data)
        return struct.pack('>i', len(data)) + data

    def _unpack(self, data):
        data = pickle.loads(data)
        return data

    def merge_verification(self):
        """ Sends an IQ to verify if there's a conflict or not.
        """

        iq = self.Iq(sto=config.server, stype='set')
        iq['merge']['node'] = 'synapse'

        # TODO: catch the possible exception
        iq.send()

    def _pubsub_event(self, msg):
        if msg['type'] in ('normal', 'headline'):
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            items = msg['pubsub_event']['items']['substanzas']

            for item in items:
                if isinstance(item, EventItem):
                    self.logger.info(item['payload'].get('status'))

        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])
