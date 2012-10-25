import os
import sys
import pickle
import struct
import uuid
import time

from threading import Event

from sleekxmpp import ClientXMPP
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream.tostring import tostring
from sleekxmpp.exceptions import IqError
from sleekxmpp.plugins.xep_0060.stanza.pubsub_event import EventItem

from baboon.baboon.monitor import FileEvent
from baboon.baboon.config import config
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common import pyrsync
from baboon.common.stanza import rsync
from baboon.common.errors.baboon_exception import BaboonException


@logger
class CommonTransport(ClientXMPP):

    def __init__(self):
        """ Initializes the CommonTranport with the XEP-0060 support.
        """

        ClientXMPP.__init__(self, config['user']['jid'], config['user'][
            'passwd'])

        self.connected = Event()
        self.disconnected = Event()
        self.rsync_running = Event()
        self.rsync_finished = Event()
        self.wait_close = False
        self.failed_auth = False

        # Register and configure pubsub plugin.
        self.register_plugin('xep_0060')
        self.register_handler(Callback('Pubsub event', StanzaPath(
            'message/pubsub_event'), self._pubsub_event))

        # Shortcut to access to the xep_0060 plugin.
        self.pubsub = self.plugin["xep_0060"]

        # Register and configure data form plugin.
        self.register_plugin('xep_0004')

        # Shortcuts to access to the xep_0004 plugin.
        self.form = self.plugin['xep_0004']

        # Shortcuts to access to the config server information
        self.pubsub_addr = config['server']['pubsub']
        self.server_addr = config['server']['master']

        # Register events
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('failed_auth', self._on_failed_auth)
        self.add_event_handler('stream_error', self.stream_err)
        self.add_event_handler('message', self.message)
        self.add_event_handler('message_form', self.message_form)
        self.add_event_handler('message_xform', self.message_form)
        self.register_handler(Callback('RsyncFinished Handler',
                                       StanzaPath('iq@type=set/rsyncfinished'),
                                       self._handle_rsync_finished))

        eventbus.register('new-rsync', self._on_new_rsync)

    def __enter__(self):
        """ Adds the support of with statement with all CommonTransport
        classes. A new XMPP connection is instantiated and returned when the
        connection is established.
        """

        # Open a new connection.
        self.open()

        # Wait until the connection is established. Raise a BaboonException if
        # there's an authentication error.
        while not self.connected.is_set():
            if self.failed_auth:
                raise BaboonException("Authentication failed.")
            self.connected.wait(1)

        # Return the instance itself.
        return self

    def __exit__(self, type, value, traceback):
        """ Disconnects the transport at the end of the with statement.
        """

        self.close()

    def open(self, block=False):
        """ Connects to the XMPP server.
        """

        self.logger.debug("Connecting to XMPP...")
        self.use_ipv6 = False
        if self.connect(use_ssl=False, use_tls=False):
            self.logger.debug("Connected to XMPP")
            self.disconnected.clear()
            self.process(block=block)
        else:
            self.logger.error("Unable to connect.")

    def stream_err(self, iq):
        """ Called when a StreamError is received.
        """

        self.logger.error(iq['text'])

    def  _on_failed_auth(self, event):
        """ Called when authentication failed.
        """

        self.logger.error("Authentication failed.")
        eventbus.fire('failed-auth')
        self.failed_auth = True
        self.close()

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        self.connected.set()
        self.logger.debug('Connected')

    def close(self):
        """ Closes the XMPP connection.
        """

        self.connected.clear()
        self.logger.debug('Closing the XMPP connection...')
        self.disconnect(wait=True)
        self.disconnected.set()
        self.logger.debug('XMPP connection closed.')

    def _pubsub_event(self, msg):
        """ Called when a pubsub event is received.
        """

        if msg['type'] in ('normal', 'headline'):
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            items = msg['pubsub_event']['items']['substanzas']
            for item in items:
                if isinstance(item, EventItem):
                    self.logger.info(item['payload'].get('status'))
                    for err_f in item['payload']:
                        if err_f.text:
                            self.logger.warning("> %s" % err_f.text)
        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])

    def _on_new_rsync(self, project, files, **kwargs):
        """ Called when a new rsync needs to be started.
        """

        self.rsync(project, files=files)
        eventbus.fire('rsync-finished-success', project, files)

    def _handle_rsync_finished(self, iq):
        """ Called when a rsync is finished.
        """

        # Retrieve the project context.
        node = iq['rsyncfinished']['node']

        # Reply to the iq.
        self.logger.debug("[%s] Sync finished." % node)
        iq.reply().send()

        # Set the rsync flags.
        self.rsync_running.clear()
        self.rsync_finished.set()

        # It's time to verify if there's a conflict or not.
        if not self.wait_close:
            self.merge_verification(node)

    def message_form(self, form):
        self.logger.debug("Received a form message: %s" % form)
        try:
            expected_type = \
                'http://jabber.org/protocol/pubsub#subscribe_authorization'
            if expected_type in form['form']['fields']['FORM_TYPE']['value']:
                node = form['form']['fields']['pubsub#node']['value']
                user = form['form']['fields']['pubsub#subscriber_jid']['value']

                self.logger.info("%s wants to join the %s project !" % (user,
                                                                        node))
                self.logger.info("You can accept the invitation request by "
                                 "running: $ baboon accept %s %s" % (node,
                                                                     user))
                self.logger.info("Or you can reject it by running: $ baboon "
                                 "reject %s %s" % (node, user))
        except KeyError:
            pass

    def message(self, msg):
        self.logger.info("Received: %s" % msg)

    def rsync_error(self, msg):
        """ On rsync error.
        """

        self.logger.error(msg)

        # Set the rsync flags.
        self.rsync_running.clear()
        self.rsync_finished.set()


@logger
class WatchTransport(CommonTransport):
    """ The transport has the responsability to communicate via HTTP
    with the baboon server and to subscribe with XMPP 0060 with the
    Baboon XMPP server.
    """

    def __init__(self):
        """ WatchTransport initializes all SleekXMPP stuff like plugins,
        events and more.
        """

        super(WatchTransport, self).__init__()

        # Shortcuts to access to the config server information
        self.streamer_addr = config['server']['streamer']

        self.register_plugin('xep_0050')  # Ad-hoc command
        self.register_plugin('xep_0065')  # Socks5 Bytestreams
        self.add_event_handler('socks_recv', self.on_recv)

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        super(WatchTransport, self).start(event)

        # Shortcut to access to the xep_0050 plugin.
        self.adhoc = self.plugin["xep_0050"]

        # Shortcut to access to the xep_0065 plugin.
        self.streamer = self.plugin["xep_0065"]

        # Negotiates the bytestream
        try:
            streamhost_used = self.streamer.handshake(self.server_addr,
                                                      self.streamer_addr)
        except IqError as e:
            self.logger.error("Cannot established the socket connection. "
                              "Exiting...")
            # If the socks5 bytestream can't be established, disconnect the
            # XMPP connection clearly.
            self.close()
            return

        # Registers the SID to retrieve later to send/recv data to the
        # good socket stored in self.streamer.proxy_threads dict.
        self.sid = streamhost_used['socks']['sid']

        # Retrieve the list of pending users.
        for project in config['projects']:
            self._get_pending_users(project)

    def close(self):
        """ Closes the XMPP connection.
        """

        # Wait until all syncs are finished.
        self.wait_close = True
        if self.rsync_running.is_set():
            self.logger.info("A sync task is currently running...")
            self.rsync_finished.wait()
            self.logger.info("Ok, all syncs are now finished.")

        # Close the proxy socket.
        if hasattr(self, 'streamer') and self.streamer:
            self.streamer.close()

        # Disconnect...
        super(WatchTransport, self).close()

    def rsync(self, project, files=None):
        """ Starts a rsync transaction, rsync and stop the
        transaction.

        Raises a BaboonException if there's a problem.
        """

        # Verify if the connection is established. Otherwise, wait...
        if not self.connected.is_set():
            self.connected.wait()

        # Set the rsync flags.
        self.rsync_running.set()
        self.rsync_finished.clear()

        #TODO: make this an int while checking config file
        max_stanza_size = int(config['server']['max_stanza_size'])

        # Build first stanza
        iq = self._build_iq(project, files)

        try:
            # Get the size of the stanza
            to_xml = tostring(iq.xml)
            size = sys.getsizeof(to_xml)

            # If it's bigger than the max_stanza_size, split it !
            if size >= max_stanza_size:
                iqs = self._split_iq(size, project, files)
                self.logger.warning('The xml stanza has been split %s stanzas.'
                                    % len(iqs))
            else:
                # Else the original iq will be the only element to send
                iqs = [iq]

            # Send elements in list
            for iq in iqs:
                iq.send()
                self.logger.debug('Sent (%d/%d)!' %
                                  (iqs.index(iq) + 1, len(iqs)))

        except IqError as e:
            self.rsync_error(e.iq['error']['text'])
        except Exception as e:
            self.rsync_error(e)

    def _build_iq(self, project, files):
        """Build a single rsync stanza.
        """
        iq = self.Iq(sto=self.server_addr, stype='set')

        # Generate a new rsync ID.
        iq['rsync']['sid'] = self.sid
        iq['rsync']['rid'] = str(uuid.uuid4())
        iq['rsync']['node'] = project

        for f in files:
            if f.event_type == FileEvent.MODIF:
                iq['rsync'].add_file(f.src_path)
            elif f.event_type == FileEvent.CREATE:
                iq['rsync'].add_create_file(f.src_path)
            elif f.event_type == FileEvent.DELETE:
                iq['rsync'].add_delete_file(f.src_path)

        return iq

    def _split_iq(self, size, project, files):
        """Splits a stanza into multiple stanzas whith size < max_stanza_size.
        Returns a list a stanzas
        """

        iqs = []

        # We don't need the exact result of the division. Let's add 1 to
        # overcome "round" issues. How many chunks do we need ?
        chunk_num = size / int(config['server']['max_stanza_size']) + 1

        # How many files per chunk then ?
        step = len(files) / chunk_num

        # Get the splitted files list
        chunks = list(self._get_chunks(files, step))

        # Build a stanza for each of them
        for chunk in chunks:
            iqs.append(self._build_iq(project, chunk))

        return iqs

    def _get_chunks(self, files, step):
        """ Generate the chunks from the files list.
        """
        for i in xrange(0, len(files), step):
            yield files[i:i + step]

    def on_recv(self, payload):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        deltas = []  # The list of delta.

        # Sets the future socket response dict.
        ret = {'from': self.boundjid.bare}

        # Unpacks the recv data.
        recv = payload['data']
        data = self._unpack(recv)

        # Gets the current project.
        ret['node'] = data['node']

        # Gets the RID.
        ret['rid'] = data['rid']

        # Gets the list of hashes.
        all_hashes = data['hashes']

        for elem in all_hashes:
            # 'elem' is a tuple. The first element is the relative
            # path to the current file. The second is the server-side
            # hashes associated to this path.
            relpath = elem[0]
            hashes = elem[1]

            # TODO: Handle the possible AttributeError.
            project_path = config['projects'][data['node']]['path']
            project_path = os.path.expanduser(project_path)

            fullpath = os.path.join(project_path, relpath)
            if os.path.exists(fullpath) and os.path.isfile(fullpath):
                # Computes the local delta of the current file.
                patchedfile = open(fullpath, 'rb')
                delta = pyrsync.rsyncdelta(patchedfile, hashes,
                                           blocksize=8192)
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

    def merge_verification(self, project):
        """ Sends an IQ to verify if there's a conflict or not.
        """

        iq = self.Iq(sto=self.server_addr, stype='set')
        iq['merge']['node'] = project

        try:
            iq.send()
        except IqError as e:
            self.logger.error(e.iq['error']['text'])

    def _get_pending_users(self, node):
        """ Build and send the message to get the list of pending users on the
        node.
        """

        # Build the IQ.
        iq = self.Iq(sto=self.pubsub_addr, stype='set')
        iq['command']['action'] = 'execute'
        iq['command']['sessionid'] = 'pubsub-get-pending:20031021T150901Z-600'
        iq['command']['node'] = 'http://jabber.org/protocol/pubsub#get-pending'
        iq['command']['form'].add_field(var='pubsub#node', value=node)

        # Send the IQ to the pubsub server !
        try:
            iq.send()
        except IqError:
            pass


@logger
class AdminTransport(CommonTransport):

    def __init__(self, logger_enabled=True):

        super(AdminTransport, self).__init__()
        self.logger.disabled = not logger_enabled

    def create_project(self, project):
        """ Creates a node on the XMPP server with the name project. Sets also
        the correct subscriptions and affiliations.
        """

        try:
            # Update the default configuration to have 'Authorize' node access
            # model.
            node_config = self.pubsub.get_node_config(self.pubsub_addr)
            node_config_form = node_config['pubsub_owner']['default']['config']
            node_config_form.field['pubsub#access_model'].set_value(
                'authorize')
            node_config_form.field['pubsub#notify_delete'].set_value(True)

            # Create the node (name == project).
            self.pubsub.create_node(self.pubsub_addr, project,
                                    config=node_config_form)

            # The owner must subscribe to the node to receive the alerts.
            self.pubsub.modify_subscriptions(self.pubsub_addr, project,
                                             [(config['user']['jid'],
                                               'subscribed')])

            # The admin must have the owner affiliation to publish alerts
            # into the node.
            self.pubsub.modify_affiliations(self.pubsub_addr, project,
                                            [(self.server_addr, 'owner')])

            return (200, 'The project %s is successfuly created.' % project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong during the creation of the project " \
                "%s." % project

            if status_code == 409:
                msg = 'The project %s already exists.' % project

            return (status_code, msg)

    def delete_project(self, project):

        try:
            self.pubsub.delete_node(self.pubsub_addr, project)
            return (200, 'The project %s is successfuly deleted.' % project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong during the deletion of the project " \
                "%s." % project

            if status_code == 403:
                msg = 'You are not authorized to delete %s project.' % project
            elif status_code == 404:
                msg = 'The project %s does not exist.' % project

            return (status_code, msg)

    def join_project(self, project):
        try:
            # TODO: Before the subscription, we need to verify if the user is
            # not already subscribed in order to have a correct message.
            # Otherwise, the status code is 202. Strange behavior.
            ret_iq = self.pubsub.subscribe(self.pubsub_addr, project)
            status = ret_iq['pubsub']['subscription']['subscription']

            if status == 'pending':
                return (202, "Invitation sent. You need to wait until the "
                        "owner accepts your invitation.")
            elif status == 'subscribed':
                return (200, "You are now a contributor of the %s project." %
                        project)
            else:
                return (500, "Something went wrong. Cannot join the %s "
                        "project." % project)

        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong. Cannot join the %s project." % project

            if status_code == 404:
                msg = "The %s project does not exist." % project

            return (status_code, msg)

    def unjoin_project(self, project):

        try:
            self.pubsub.unsubscribe(self.pubsub_addr, project)
            return (200, "Successfully unjoin the %s project." % project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong. Cannot unjoin the %s project." \
                  % project

            if status_code == 401:
                msg = "You are not a contributor of the %s project." % project
            elif status_code == 404:
                msg = "The %s project does not exist." % project

            return (status_code, msg)

    def get_project_users(self, project):
        try:
            ret = self.pubsub.get_node_subscriptions(self.pubsub_addr, project)
            return ret['pubsub_owner']['subscriptions']
        except IqError:
            # TODO: Handle this error.
            pass

    def accept_pending(self, project, user):
        self._allow_pending(project, user, 'true')
        return (200, "%s is now successfuly subscribed on %s." % (user,
                                                                  project))

    def reject(self, project, user):
        self._allow_pending(project, user, 'false')
        return (200, "%s is now successfuly rejected on %s." % (user,
                                                                project))

    def kick(self, project, user):

        subscriptions = [(user, 'none')]
        try:
            self.pubsub.modify_subscriptions(self.pubsub_addr, project,
                                             subscriptions=subscriptions)
            return (200, "%s is now successfuly kicked from %s." % (user,
                                                                    project))
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong."

            if status_code == 403:
                msg = "You don't have the permission to do this."
            elif status_code == 404:
                msg = "The %s project does not exist." % project

            return (status_code, msg)

    def first_git_init(self, project, url):

        iq = self.Iq(sto=self.server_addr, stype='set')
        iq['git-init']['node'] = project
        iq['git-init']['url'] = url

        try:
            iq.send(timeout=240)
            return (200, "The project %s is now correctly initialized." %
                    project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong."

            if status_code == 503:
                msg = e.iq['error']['text']

            return (status_code, msg)

    def _allow_pending(self, project, user, allow):
        """ Build and send the message to accept/reject the user on the node
        project depending on allow boolean.
        """

        # Build the data form.
        payload = self.form.make_form(ftype='submit')
        payload.add_field(var='FORM_TYPE', ftype='hidden',
                          value='http://jabber.org/protocol/pubsub'
                          '#subscribe_authorization')
        payload.add_field(var='pubsub#subid', value='ididid')
        payload.add_field(var='pubsub#node', value=project)
        payload.add_field(var='pubsub#subscriber_jid', value=user)
        payload.add_field(var='pubsub#allow', value=allow)

        # Build the message.
        message = self.make_message(self.pubsub_addr)
        message.appendxml(payload.xml)

        # Send the message to the pubsub server !
        message.send()


class RegisterTransport(CommonTransport):

    def __init__(self, callback=None):

        super(RegisterTransport, self).__init__()

        self.callback = callback

        self.register_plugin('xep_0077')  # In-band Registration
        self.add_event_handler('register', self.register)

    def register(self, iq):
        """ Handler for the register event.
        """

        resp = self.Iq()
        resp['type'] = 'set'
        resp['register']['username'] = self.boundjid.user
        resp['register']['password'] = self.password

        try:
            resp.send(now=True)

            if self.callback:
                self.callback(200, 'You are now registered as %s.' %
                              config['user']['jid'])
        except IqError as e:
            if self.callback:
                status_code = int(e.iq['error']['code'])
                msg = "Something went wrong during the registration."

                if status_code == 409:
                    msg = "This username is already use. Please choose " \
                          "another one."
                elif status_code == 500:
                    # Often, registration limit exception.
                    msg = e.iq['error']['text']

                self.callback(status_code, msg, fatal=True)

        self.close()
