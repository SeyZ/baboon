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

        # Registers pending rsyncs.
        self.rsyncs = {}

        self.use_ipv6 = False
        if self.connect(use_ssl=False, use_tls=False):
            self.process()

    def _handle_rsync(self, iq):
        sid = iq['rsync']['sid']  # Registers the SID.
        sfrom = '%s' % iq['from'].bare  # Registers the bare JID.
        files = iq['rsync']['files']
        del_files = iq['rsync']['delete_files']
        project_name = iq['rsync']['node']
        project_path = os.path.join(config.working_dir, project_name,
                                    sfrom)

        # Delete the files if there're filepaths in del_files.
        if del_files:
            for f in del_files:
                try:
                    full_del_path = os.path.join(project_path, f)
                    os.unlink(full_del_path)
                    self.logger.info('File deleted: %s' % full_del_path)
                except OSError:
                    # There's no problem if the file does not exists.
                    pass

        # Log a info message if there're files to sync.
        if files:
            self.logger.info('[%s] - Need to sync %s from %s.' %
                             (project_name, files, sfrom))

        # Replies to the IQ
        reply = iq.reply()
        reply['rsync']

        # Registers the reply iq to the rsyncs dict. This result IQ
        # will be sent when the rsync is completely finished.
        self.rsyncs[sid] = reply

        # Sets the future socket response dict.
        ret = {'sid': sid}

        # A list of hashes.
        all_hashes = []

        for relpath in files:
            fullpath = os.path.join(project_path, relpath)
            # Computes the block checksums. If the file does not
            # exist, create it.
            unpatched = open(fullpath, 'w+b')
            hashes = pyrsync.blockchecksums(unpatched)

            data = (relpath, hashes)
            all_hashes.append(data)

        # Adds the hashes list in the ret dict.
        ret['hashes'] = all_hashes

        # Sends over the streamer.
        self.streamer.send(sid, self._pack(ret))

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

    def get_nodes(self):
        return self.pubsub.get_nodes(config.pubsub)

    def create_node(self, node):
        self.pubsub.create_node(config.pubsub, node)

    def delete_node(self, node):
        return self.pubsub.delete_node(config.pubsub, node)

    def on_recv(self, payload):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        sid = payload['sid']
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
            shutil.copy(save_fd.name, path)

            # Deletes the file.
            os.remove(save_fd.name)

        # Gets the reply IQ associated to the SID.
        reply_iq = self.rsyncs.get(sid)
        if reply_iq:
            # The rsync is completely finished. It's time to send the
            # reply IQ to warn the client-side.
            reply_iq.send()

            # Removes the pending rsync from the rsyncs dict.
            del self.rsyncs[sid]
        else:
            # TODO: Handle this error.
            pass

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
