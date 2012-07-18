import os
import shutil
import struct
import tempfile
import pickle
import executor

import executor
import task

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

        self.add_event_handler('session_start', self.start)
        self.add_event_handler('socks_recv', self.on_recv)

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
        self.logger.info('Received rsync stanza !')

        sid = iq['rsync']['sid']  # Registers the SID.
        rid = iq['rsync']['rid']  # Register the RID.
        sfrom = '%s' % iq['from'].bare  # Registers the bare JID.
        files = iq['rsync']['files']  # Get the files list to sync.
        node = iq['rsync']['node']  # Get the current project name.

        # Get the project path.
        project_path = os.path.join(config.working_dir, node, sfrom)

        # Prepare the **kwargs argument for the RsyncTask contructor.
        kwargs = {
            'sid': sid,
            'rid': rid,
            'sfrom': sfrom,
            'project_path': project_path,
            'files': files,
        }

        # Put the rsync task in the tasks queue.
        self.logger.debug('Prepared rsync task %s' % rid)

        # TODO: Don't register the rsync_task globally to the class.
        rsync_task = task.RsyncTask(**kwargs)
        executor.tasks.put(rsync_task)

        # Register the current rsync_task in the pending_rsyncs dict.
        self.pending_rsyncs[rid] = rsync_task

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

        # Declare a pending_rsyncs dict with key -> SID and value the
        # rsync_task object.
        self.pending_rsyncs = {}

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
        rid = recv['rid']  # The rsync ID.

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

        # Get the rsync task associated to the sid to set() the rsync_finished
        # Event.
        cur_rsync_task = self.pending_rsyncs.get(rid)
        if cur_rsync_task:
            cur_rsync_task.rsync_finished.set()
        else:
            self.logger.error('Rsync task %s not found.' % rid)
            # TODO: Handle this error.

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
