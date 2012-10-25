import os
import shutil
import subprocess
import struct
import tempfile
import pickle

from threading import Event
from os.path import join

from sleekxmpp import ClientXMPP
from sleekxmpp.jid import JID
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath

from baboon.baboond.dispatcher import dispatcher
from baboon.baboond.config import config
from baboon.common.stanza.rsync import MergeStatus
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common import pyrsync


@logger
class Transport(ClientXMPP):
    """ The transport has the responsability to communicate with the
    sleekxmpp library via XMPP protocol.
    """

    def __init__(self):

        ClientXMPP.__init__(self, config['user']['jid'], config['user'][
            'passwd'])

        self.register_plugin('xep_0060')  # PubSub
        self.register_plugin('xep_0065')  # Socks5 Bytestreams
        self.pubsub_addr = config['server']['pubsub']
        self.working_dir = config['server']['working_dir']

        # Some shortcuts
        self.pubsub = self.plugin['xep_0060']
        self.streamer = self.plugin['xep_0065']

        self.disconnected = Event()
        self.pending_rsyncs = {}   # {SID => RsyncTask}
        self.pending_git_init_tasks = {}  # {BID => GitInitTask}

        # Bind all handlers to corresponding events.
        self._bind()

        # Start the XMPP connection.
        self.use_ipv6 = False
        if self.connect(use_ssl=False, use_tls=False):
            self.disconnected.clear()
            self.process()

    def close(self):
        """ Disconnect from the XMPP server.
        """

        self.streamer.close()
        self.disconnect(wait=True)
        self.disconnected.set()
        self.logger.info("Disconnected from the XMPP server.")

    def alert(self, node, msg, files=[]):
        """ Build a MergeStatus stanza and publish it to the pubsub node.
        """

        # Build the MergeStatus stanza.
        status_msg = MergeStatus()
        status_msg['node'] = node
        status_msg['status'] = msg
        status_msg.set_files(files)

        try:
            result = self.pubsub.publish(self.pubsub_addr, node,
                                         payload=status_msg)
            self.logger.debug("Published a msg to the node: %s" % node)
        except:
            self.logger.debug("Could not publish to: %s" % node)

    def _bind(self):
        """ Registers needed handlers.
        """

        self.add_event_handler('session_start', self._on_session_start)
        self.add_event_handler('failed_auth', self._on_failed_auth)
        self.add_event_handler('socks_recv', self._on_socks5_data)

        self.register_handler(Callback('First Git Init Handler',
                                       StanzaPath('iq@type=set/git-init'),
                                       self._on_git_init_stanza))

        self.register_handler(Callback('RsyncStart Handler',
                                       StanzaPath('iq@type=set/rsync'),
                                       self._on_rsync_stanza))

        self.register_handler(Callback('MergeVerification Handler',
                                       StanzaPath('iq@type=set/merge'),
                                       self._on_merge_stanza))

        eventbus.register('rsync-finished-success', self._on_rsync_success)
        eventbus.register('rsync-finished-failure', self._on_rsync_failure)
        eventbus.register('git-init-success', self._on_git_init_success)
        eventbus.register('git-init-failure', self._on_git_init_failure)

    def _on_session_start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        self.logger.info("Connected to the XMPP server.")

    def _on_failed_auth(self, event):
        """ Called when authentication failed.
        """

        self.logger.error("Authentication failed.")
        eventbus.fire('failed-auth')
        self.close()

    def _on_git_init_stanza(self, iq):
        """ Called when a GitInit stanza is received. This handler creates a
        new GitInitTask if permissions are good.
        """

        self.logger.info("Received a git init stanza.")

        # Get the useful data.
        node = iq['git-init']['node']
        url = iq['git-init']['url']
        sfrom = iq['from'].bare

        # Ensure permissions.
        is_subscribed = self._verify_subscription(iq, sfrom, node)
        if not is_subscribed:
            eventbus.fire("rsync-finished-failure")
            return

        # Create a new GitInitTask
        from baboon.baboond.task import GitInitTask
        git_init_task = GitInitTask(node, url, sfrom)

        # Register the BaboonId of this GitInitTask in the
        # self.pending_git_init_tasks dict.
        self.pending_git_init_tasks[git_init_task.bid] = iq

        # Add the GitInitTask to the list of tasks to execute.
        dispatcher.put(node, git_init_task)

    def _on_rsync_stanza(self, iq):
        """ Called when a Rsync stanza is received. This handler creates a
        new RsyncTask if permissions are good.
        """

        self.logger.info('Received a rsync stanza.')

        # Get the useful data.
        node = iq['rsync']['node']
        sid = iq['rsync']['sid']
        rid = iq['rsync']['rid']
        files = iq['rsync']['files']
        sfrom = iq['from']
        project_path = join(self.working_dir, node, sfrom.bare)

        # Verify if the user is a subscriber/owner of the node.
        is_subscribed = self._verify_subscription(iq, sfrom.bare, node)
        if not is_subscribed:
            eventbus.fire('rsync-finished-failure', rid=rid)
            return

        # The future reply iq.
        reply = iq.reply()

        # Create the new RsyncTask.
        from task import RsyncTask
        rsync_task = RsyncTask(sid, rid, sfrom, node, project_path, files)
        dispatcher.put(node, rsync_task)

        # Register the current rsync_task in the pending_rsyncs dict.
        self.pending_rsyncs[rid] = rsync_task

        # Reply to the IQ
        reply['rsync']
        reply.send()

    def _on_merge_stanza(self, iq):
        """ Called when a MergeVerification stanza is received. This handler
        creates a new MergeTask if permissions are good.
        """

        # Get the useful data.
        sfrom = iq['from'].bare
        node = iq['merge']['node']
        project_path = join(self.working_dir, node, sfrom)

        # Verify if the user is a subscriber/owner of the node.
        is_subscribed = self._verify_subscription(iq, sfrom, node)
        if not is_subscribed:
            eventbus.fire("rsync-finished-failure")
            return

        # Verify if the server-side project is a git repository.
        is_git_repo = self._verify_git_repository(iq, node, project_path)
        if not is_git_repo:
            return

        # The future reply iq.
        reply = iq.reply()

        # Prepare the merge verification with this data.
        from task import MergeTask
        dispatcher.put(node, MergeTask(node, sfrom))

        # Reply to the request.
        reply.send()

    def _on_socks5_data(self, payload):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        self.logger.debug("Received data over socks5 socket.")

        # Unpack the payload.
        data = self._unpack(payload['data'])

        # Get the useful data.
        node = data['node']
        rid = data['rid']
        sfrom = JID(data['from'])
        deltas = data['delta']
        project_path = join(self.working_dir, node, sfrom.bare)

        # Patch files with corresponding deltas.
        for relpath, delta in deltas:
            self._patch_file(join(project_path, relpath), delta)

        cur_rsync_task = self.pending_rsyncs.get(rid)
        if cur_rsync_task:
            cur_rsync_task.rsync_finished.set()
        else:
            self.logger.error('Rsync task %s not found.' % rid)
            # TODO: Handle this error.

    def _on_git_init_success(self, bid):
        """ Called when a git init task has been terminated successfuly.
        """

        # Retrieve the IQ associated to this BaboonId and send the response.
        iq = self.pending_git_init_tasks[bid]
        if not iq:
            self.logger.error("IQ associated with the %s BID not found." % bid)

        # Send the reply iq.
        iq.reply().send()

        # Remove the entry in the pending dict.
        del self.pending_git_init_tasks[bid]

    def _on_git_init_failure(self, bid, error):
        """ Called when a git init task has been terminated with an error.
        """

        # Display the error message.
        self.logger.error(error)

        # Retrieve the IQ associated to this BaboonId and send the response.
        iq = self.pending_git_init_tasks[bid]
        if not iq:
            self.logger.error("IQ associated with the %s BID not found." % bid)
            return

        # Send the reply error iq.
        reply = iq.reply().error()
        reply['error']['code'] = '409'
        reply['error']['type'] = 'cancel'
        reply['error']['condition'] = 'conflict'
        reply['error']['text'] = error
        reply.send()

        # Remove the entry in the pending dict.
        del self.pending_git_init_tasks[bid]

    def _on_rsync_success(self, rid, *args, **kwargs):
        """ Called when a rsync task has been terminated successfuly.
        """
        cur_rsync_task = self.pending_rsyncs.get(rid)
        if cur_rsync_task:
            self.logger.debug("RsyncTask %s finished." % rid)
            iq = self.Iq(sto=cur_rsync_task.jid, stype='set')
            iq['rsyncfinished']['node'] = cur_rsync_task.project
            iq.send(block=False)
        else:
            self.logger.error("Could not find a rsync task with RID: %s" % rid)

    def _on_rsync_failure(self, *args, **kwargs):
        """ Called when a rsync task has been terminated with an error.
        """

        rid = kwargs.get('rid')
        if rid is None:
            return

        cur_rsync_task = self.pending_rsyncs.get(rid)
        if cur_rsync_task:
            self.logger.debug("RsyncTask %s finished with an error." % rid)

            # TODO: Add a status (success/error) to the rsyncfinished iq.
            iq = self.Iq(sto=cur_rsync_task.jid, stype='set')
            iq['rsyncfinished']['node'] = cur_rsync_task.project
            iq.send(block=False)

    def _pack(self, data):
        data = pickle.dumps(data)
        return struct.pack('>i', len(data)) + data

    def _unpack(self, data):
        data = pickle.loads(data)
        return data

    def _verify_subscription(self, iq, jid, node):
        """ Verify if the bare jid is a subscriber/owner on the node.
        """

        try:
            ret = self.pubsub.get_node_subscriptions(self.pubsub_addr, node)
            subscriptions = ret['pubsub_owner']['subscriptions']

            for subscription in subscriptions:
                if jid == subscription['jid']:
                    return True
        except Exception as e:
            pass

        err_msg = "you are not a contributor on %s." % node
        self._send_forbidden_error(iq.reply(), err_msg)

        return False

    def _verify_git_repository(self, iq, node, path):
        """
        """

        proc = subprocess.Popen('git status', stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=True,
                                cwd=path)
        output, errorss = proc.communicate()

        if not proc.returncode:
            return True
        else:
            err_msg = ("The repository %s seems to be corrupted. Please, "
                       " (re)run the init command." % node)
            self._send_forbidden_error(iq.reply(), err_msg)

            return False

    def _patch_file(self, fullpath, delta):
        """ Patch the fullpath file with the delta.
        """

        # Open the unpatched file with the cursor at the beginning.
        unpatched = open(fullpath, 'rb')
        unpatched.seek(0)

        # Save the new file in a temporary file. Avoid to delete the file
        # when it's closed.
        save_fd = tempfile.NamedTemporaryFile(delete=False)

        # Patch the file with the delta.
        pyrsync.patchstream(unpatched, save_fd, delta)

        # Close the file (data are flushed).
        save_fd.close()

        # Rename the temporary file to the good file path.
        shutil.move(save_fd.name, fullpath)

    def _send_forbidden_error(self, iq, err_msg):
        """ Send an error iq with the err_msg as text.
        """
        iq.error()
        iq['error']['code'] = '503'
        iq['error']['type'] = 'auth'
        iq['error']['condition'] = 'forbidden'
        iq['error']['text'] = err_msg
        iq.send()


transport = Transport()
