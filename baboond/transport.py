import os
import shutil
import struct
import tempfile
import pickle
import executor

from sleekxmpp import ClientXMPP
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath

from config import config
from common.stanza.rsync import MergeStatus
from common.logger import logger
from common import pyrsync


@logger
class Transport(ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self):
        ClientXMPP.__init__(self, config.jid, config.password)
        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0065')  # Socks5 Bytestreams

        self.add_event_handler('socks_recv', self.on_recv)
        self.add_event_handler('session_start', self.start)

        self.register_handler(Callback('RsyncStart Handler',
                                       StanzaPath('iq@type=set/rsync'),
                                       self._handle_rsync))

        self.register_handler(Callback('MergeVerification Handler',
                                       StanzaPath('iq@type=set/merge'),
                                       self._handle_merge_verification))

        # Connect to the XMPP server using IPv4 only and without
        # SSL/TLS support for now.
        self.use_ipv6 = False
        if self.connect(use_ssl=False, use_tls=False):
            self.process()

    def _handle_rsync(self, iq):
        sid = iq['rsync']['sid']  # Registers the SID.
        sfrom = '%s' % iq['from'].bare  # Registers the bare JID.
        files = iq['rsync']['files']  # Get the files list to sync.
        del_files = iq['rsync']['delete_files']  # Get the file list to delete.
        node = iq['rsync']['node']  # Get the current project name.

        # Prepare the **kwargs argument for the prepare_rsync method.
        kwargs = {
            'sid': sid,
            'sfrom': sfrom,
            'node': node,
            'files': files,
            'del_files': del_files,
        }

        # Prepares the merge verification with **kwargs argument.
        executor.preparator.prepare_rsync(**kwargs)

        # Replies to the IQ
        reply = iq.reply()
        reply['rsync']
        reply.send()

    def _handle_merge_verification(self, iq):
        """ Creates a merge verification task.
        """

        sfrom = iq['from'].bare
        node = iq['merge']['node']

        # Prepares the merge verification with this data.
        executor.preparator.prepare_merge_verification(node, sfrom)

        # Replies to the request.
        iq.reply().send()

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        # Registers the plugins.
        self.pubsub = self.plugin['xep_0060']
        self.streamer = self.plugin['xep_0065']

    def close(self):
        self.streamer.close()
        self.disconnect()
        self.logger.debug('Closed the XMPP connection.')

    def on_recv(self, payload):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        recv = payload['data']

        # Unpacks the recv.
        recv = self._unpack(recv)

        # Shortcuts to useful data in recv.
        sfrom = recv['from']  # The bare jid of the requester.
        node = recv['node']  # The project name.
        deltas = recv['delta']  # A list of delta tuple.

        # Sets the current working directory.
        project_path = os.path.join(config.working_dir, node, sfrom)

        for elem in deltas:
            # Unpacks the tuple.
            relpath = elem[0]
            delta = elem[1]

            # Sets the current file fullpath.
            path = os.path.join(project_path, relpath)

            # Sets the file cursor of the unpatched file at the
            # beginning.
            unpatched = open(path, 'rb')
            unpatched.seek(0)

            # Saves the new file in a temporary file. Avoids to delete
            # the file when it's closed.
            save_fd = tempfile.NamedTemporaryFile(delete=False)

            # Let's go for the patch !
            pyrsync.patchstream(unpatched, save_fd, delta)

            # Closes the file (data are flushed).
            save_fd.close()

            # Renames the temporary file to the good file path.
            shutil.move(save_fd.name, path)

        self.logger.debug('Rsync task finished')

    def _pack(self, data):
        data = pickle.dumps(data)
        return struct.pack('>i', len(data)) + data

    def _unpack(self, data):
        data = pickle.loads(data)
        return data

    def alert(self, project_name, username, msg):
        """ Broadcast the msg on the pubsub node (written in the
        config file).
        """

        status_msg = MergeStatus()
        status_msg['node'] = project_name
        status_msg['status'] = msg

        try:
            result = self.pubsub.publish(config.pubsub,
                                         project_name,
                                         payload=status_msg)
            id = result['pubsub']['publish']['item']['id']
            self.logger.debug('Published at item id: %s' % id)
        except:
            self.logger.debug('Could not publish to: %s' %
                              project_name)

transport = Transport()
