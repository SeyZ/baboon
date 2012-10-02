import os
import shutil
import subprocess
import struct
import tempfile
import pickle

from sleekxmpp import ClientXMPP
from sleekxmpp.jid import JID
from sleekxmpp.xmlstream.handler.callback import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath

import executor
import task

from baboond.config import config
from common.stanza.rsync import MergeStatus
from common.eventbus import eventbus
from common.logger import logger
from common import pyrsync


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

        self.add_event_handler('session_start', self.start)
        self.add_event_handler('socks_recv', self.on_recv)

        self.register_handler(Callback('First Git Init Handler',
                                       StanzaPath('iq@type=set/git-init'),
                                       self._handle_git_init))

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

    def _handle_git_init(self, iq):
        self.logger.info("Received a first git initialization !")

        node = iq['git-init']['node']
        url = iq['git-init']['url']
        sfrom = iq['from'].bare

        is_subscribed = self._verify_subscription(sfrom, node)
        if not is_subscribed:
            self._send_forbidden_error(iq.reply(), "you are not a contributor "
                                       "on %s." % node)
            return

        # Create a new GitInitTask
        git_init_task = task.GitInitTask(node, url, sfrom)

        # Register the BaboonId of this GitInitTask in the
        # self.pending_git_init_tasks dict.
        self.pending_git_init_tasks[git_init_task.bid] = iq

        # Add the GitInitTask to the list of tasks to execute.
        executor.tasks.put(git_init_task)

        # Register the callbacks.
        eventbus.register_once('git-init-success', self._on_git_init_success)
        eventbus.register_once('git-init-failure', self._on_git_init_failure)

    def _on_git_init_success(self, bid):
        """ Called when a git init task has been terminated successfuly.
        """

        # Retrieve the IQ associated to this BaboonId and send the response.
        iq = self.pending_git_init_tasks[bid]
        iq.reply().send()

        # Remove the entry in the pending dict.
        del self.pending_git_init_tasks[bid]

    def _on_git_init_failure(self, bid, error):
        """ Called when a git init task has been terminated with an error.
        """

        self.logger.error(error)

        # Retrieve the IQ associated to this BaboonId and send the response.
        iq = self.pending_git_init_tasks[bid]
        reply = iq.reply().error()
        reply['error']['code'] = '409'
        reply['error']['type'] = 'cancel'
        reply['error']['condition'] = 'conflict'
        reply['error']['text'] = error
        reply.send()

        # Remove the entry in the pending dict.
        del self.pending_git_init_tasks[bid]

    def _handle_rsync(self, iq):
        self.logger.info('Received rsync stanza !')

        sid = iq['rsync']['sid']  # Registers the SID.
        rid = iq['rsync']['rid']  # Register the RID.
        sfrom = iq['from']  # Registers the bare JID.
        files = iq['rsync']['files']  # Get the files list to sync.
        node = iq['rsync']['node']  # Get the current project name.

        # The future reply stanza.
        reply = iq.reply()

        # Verify if the user is a subscriber/owner of the node.
        is_subscribed = self._verify_subscription(sfrom.bare, node)
        if not is_subscribed:
            self._send_forbidden_error(reply, "you are not a contributor on "
                                       "%s." % node)
            return

        # Get the project path.
        project_path = os.path.join(config['server']['working_dir'], node,
                                    sfrom.bare)

        # Prepare the **kwargs argument for the RsyncTask constructor.
        kwargs = {
            'sid': sid,
            'rid': rid,
            'sfrom': sfrom,
            'project': node,
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
        reply['rsync']
        reply.send()

    def _handle_merge_verification(self, iq):
        """ Creates a merge verification task.
        """

        sfrom = iq['from'].bare
        node = iq['merge']['node']

        # Get the project path.
        project_path = os.path.join(config['server']['working_dir'], node,
                                    sfrom)

        # The future reply stanza.
        reply = iq.reply()

        # Verify if the user is a subscriber/owner of the node.
        is_subscribed = self._verify_subscription(sfrom, node)
        if not is_subscribed:
            self._send_forbidden_error(reply, "You are not a contributor on "
                                       "%s." % node)
            return

        # Verify if the server-side project is a git repository.
        is_git_repo = self._verify_git_repository(project_path)
        if not is_git_repo:
            self._send_forbidden_error(reply, "The repository %s seems to be "
                                       "corruputed. Please, (re)run the init "
                                       "command." % node)
            return

        # Prepares the merge verification with this data.
        executor.tasks.put(task.MergeTask(node, sfrom))

        # Replies to the request.
        reply.send()

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

        # Declare a pending git_init_task in a dict.
        self.pending_git_init_tasks = {}

    def close(self):
        self.streamer.close()
        self.disconnect()
        self.logger.debug('Closed the XMPP connection.')

    def on_recv(self, payload):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        self.logger.debug("Received data over socks5.")
        recv = payload['data']

        # Unpacks the recv.
        recv = self._unpack(recv)

        # Shortcuts to useful data in recv.
        sfrom = JID(recv['from']).bare  # The bare jid of the requester.
        node = recv['node']  # The project name.
        deltas = recv['delta']  # A list of delta tuple.
        rid = recv['rid']  # The rsync ID.

        # Sets the current working directory.
        project_path = os.path.join(config['server']['working_dir'], node,
                                    sfrom)

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
            result = self.pubsub.publish(config['server']['pubsub'],
                                         project_name, payload=status_msg)
            id = result['pubsub']['publish']['item']['id']
            self.logger.debug('Published at item id: %s' % id)
        except:
            self.logger.debug('Could not publish to: %s' %
                              project_name)

    def send_rsync_finished(self, to):
        iq = self.Iq(sto=to, stype='set')
        iq['rsyncfinished']
        iq.send()

    def _verify_subscription(self, jid, node):
        """ Verify if the bare jid is a subscriber/owner on the node.
        """

        try:
            ret = self.pubsub.get_node_subscriptions(
                config['server']['pubsub'], node)
            subscriptions = ret['pubsub_owner']['subscriptions']

            for subscription in subscriptions:
                if jid == subscription['jid']:
                    return True
        except Exception as e:
            pass

        return False

    def _verify_git_repository(self, path):
        proc = subprocess.Popen('git status', stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, shell=True,
                                cwd=path)
        output, errorss = proc.communicate()
        return proc.returncode == 0

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
