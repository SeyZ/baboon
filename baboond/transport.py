import os
import shutil
import struct
import tempfile
import pickle
import sleekxmpp
import executor

from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath

from config import config
from common.stanza.rsync import MergeStatus
from common.logger import logger
from common import pyrsync


# Registers pending rsyncs.
rsyncs = {}


@logger
class Transport(sleekxmpp.ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self):
        sleekxmpp.ClientXMPP.__init__(self,
                                      'admin@baboon-project.org/dogwood',
                                      'secret')
        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0065')  # Socks5 Bytestreams

        self.add_event_handler('socks_recv', self.on_recv)
        self.add_event_handler('session_start', self.start)

        self.register_handler(Callback(
                'RsyncStart Handler',
                StanzaPath('iq@type=set/rsync'),
                self._handle_rsync))

        self.register_handler(Callback(
                'MergeVerification Handler',
                StanzaPath('iq@type=set/merge'),
                self._handle_merge_verification))

        if self.connect():
            self.process()

    def _handle_rsync(self, iq):
        # Registers the SID.
        sid = iq['rsync']['sid']
        sfrom = '%s' % iq['from'].bare  # Takes only the bare part of
                                        # the JID.
        project_name = iq['rsync']['node']
        project_path = os.path.join(config.working_dir, project_name,
                                    sfrom)

        # Replies to the IQ
        reply = iq.reply()
        reply['rsync']

        # Registers the reply iq to the rsyncs dict. This result IQ
        # will be sent when the rsync is completely finished.
        rsyncs[sid] = reply

        # Sets the future socket response dict.
        ret = {'sid': sid}

        # A list of hashes.
        all_hashes = []

        for path, dirs, files in os.walk(project_path):
            for filename in files:
                fullpath = os.path.join(path, filename)
                # Computes the block checksums.
                unpatched = open(fullpath, "rb")
                hashes = pyrsync.blockchecksums(unpatched)

                relpath = os.path.relpath(fullpath, project_path)
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

    def on_recv(self, recv):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        # Unpacks the recv.
        recv = self._unpack(recv)

        # Shortcuts to useful data in recv.
        sfrom = recv['from']  # The bare jid of the requester.
        node = recv['node']  # The project name.
        sid = recv['sid']  # The SID.
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
        reply_iq = rsyncs.get(sid)
        if reply_iq:
            # The rsync is completely finished. It's time to send the
            # reply IQ to warn the client-side.
            reply_iq.send()

            # Removes the pending rsync from the rsyncs dict.
            del rsyncs[sid]
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
