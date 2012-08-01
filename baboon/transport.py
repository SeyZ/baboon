import os
import sys
import pickle
import struct
import uuid

from threading import Event

from sleekxmpp import ClientXMPP
from sleekxmpp.xmlstream.handler import Callback
from sleekxmpp.xmlstream.matcher import StanzaPath
from sleekxmpp.xmlstream.tostring import tostring
from sleekxmpp.exceptions import IqError
from sleekxmpp.plugins.xep_0060.stanza.pubsub_event import EventItem

from monitor import FileEvent
from config import config
from common.logger import logger
from common import pyrsync
from common.stanza import rsync


@logger
class CommonTransport(ClientXMPP):

    def __init__(self):
        """
        """

        ClientXMPP.__init__(self, config['user']['jid'], config['user'][
            'passwd'])

        self.connected = Event()

        # Register and configure pubsub plugin.
        self.register_plugin('xep_0060')
        self.register_handler(Callback('Pubsub event', StanzaPath(
                    'message/pubsub_event'), self._pubsub_event))

        # Shortcut to access to the xep_0060 plugin.
        self.pubsub = self.plugin["xep_0060"]

        # Shortcuts to access to the config server information
        self.pubsub_addr = config['server']['pubsub']
        self.server_addr = config['server']['server']

        # Register events
        self.add_event_handler('session_start', self.start)
        self.add_event_handler('stream_error', self.stream_err)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def open(self, block=False):
        """ Connects to the XMPP server.
        """

        self.logger.debug("Connecting to XMPP...")
        self.use_ipv6 = False
        if self.connect(use_ssl=False, use_tls=False):
            self.logger.debug("Connected to XMPP")
            self.process(block=block)
        else:
            self.logger.error("Unable to connect.")

    def stream_err(self, iq):
        self.logger.error(iq['text'])

    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        self.send_presence()
        self.get_roster()

        self.connected.set()
        self.logger.info('Connected')

    def close(self):
        """ Closes the XMPP connection.
        """

        self.connected.clear()
        self.disconnect()
        self.logger.debug('Closed the XMPP connection')

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

        self.register_plugin('xep_0065')  # Socks5 Bytestreams
        self.add_event_handler('socks_recv', self.on_recv)


    def start(self, event):
        """ Handler for the session_start sleekxmpp event.
        """

        super(WatchTransport, self).start(event)

        self.pending_rsyncs = {}

        # Shortcut to access to the xep_0065 plugin.
        self.streamer = self.plugin["xep_0065"]

        # Negotiates the bytestream
        streamhost_used = self.streamer.handshake(config['server']['server'],
                                                  config['server']['streamer'])

        # Registers the SID to retrieve later to send/recv data to the
        # good socket stored in self.streamer.proxy_threads dict.
        self.sid = streamhost_used['socks']['sid']

    def close(self):
        """ Closes the XMPP connection.
        """

        # Close the proxy socket.
        self.streamer.close()

        # Disconnect...
        super(WatchTransport, self).close()


    def rsync(self, files=None):
        """ Starts a rsync transaction, rsync and stop the
        transaction.

        Raises a BaboonException if there's a problem.
        """

        iq = self.Iq(sto=config['server']['server'], stype='set')

        # Generate a new rsync ID.
        iq['rsync']['sid'] = self.sid
        iq['rsync']['rid'] = str(uuid.uuid4())
        iq['rsync']['node'] = config.node

        for f in files:
            if f.event_type == FileEvent.MODIF:
                iq['rsync'].add_file(f.src_path)
            elif f.event_type == FileEvent.CREATE:
                iq['rsync'].add_create_file(f.src_path)
            elif f.event_type == FileEvent.DELETE:
                iq['rsync'].add_delete_file(f.src_path)

        try:
            self.logger.info('Sending a rsync stanza !')
            to_xml = tostring(iq.xml)
            if sys.getsizeof(to_xml) >= config.max_stanza_size:
                self.logger.warning('The xml stanza is too big !')
            else:
                iq.send(block=False)
                self.logger.info('Sent !')
        except IqError as e:
            self.logger.error(e.iq)
        except Exception as e:
            self.logger.error(e)

    def on_recv(self, payload):
        """ Called when receiving data over the socks5 socket (xep
        0065).
        """

        deltas = []  # The list of delta.

        # Sets the future socket response dict.
        ret = {'from': self.boundjid.bare,
               'node': config.node,
               }

        # Unpacks the recv data.
        recv = payload['data']
        data = self._unpack(recv)

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

            fullpath = os.path.join(config.path, relpath)
            if os.path.exists(fullpath) and os.path.isfile(fullpath):
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

        iq = self.Iq(sto=self.server_addr, stype='set')
        iq['merge']['node'] = config.node

        # TODO: catch the possible exception
        iq.send()

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

            # Create the node (name == project).
            self.pubsub.create_node(self.pubsub_addr, project,
                    config=node_config_form)

            # The owner must subscribe to the node to receive the alerts.
            self.pubsub.modify_subscriptions(self.pubsub_addr, project,
                    [(config['user']['jid'], 'subscribed')])

            # The admin must have the publisher affiliation to publish alerts
            # into the node.
            self.pubsub.modify_affiliations(self.pubsub_addr, project,
                    [(self.server_addr,'publisher')])

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
                msg = "The %s project does not exist." %  project

            return (status_code, msg)

    def unjoin_project(self, project):

        try:
            self.pubsub.unsubscribe(self.pubsub_addr, project)
            return (200, "Successfully unjoin the %s project." % project)
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong. Cannot unjoin the %s project." % \
                    project

            if status_code == 401:
                msg = "You are not a contributor of the %s project." % project
            elif status_code == 404:
                msg = "The %s project does not exist." %  project

            return (status_code, msg)

    def get_project_users(self, project):
        try:
            ret = self.pubsub.get_node_subscriptions(self.pubsub_addr, project)
            return ret['pubsub_owner']['subscriptions']
        except IqError:
            # TODO: Handle this error.
            pass

    def accept_pending(self, project, users):

        # TODO: accept only pending users, not all. (ref.
        # http://xmpp.org/extensions/xep-0060.html#owner-subreq-process)

        subscriptions = []
        for user in users:
            subscriptions.append((user, 'subscribed'))

        try:
            self.pubsub.modify_subscriptions(self.pubsub_addr, project,
                    subscriptions=subscriptions)
            return (200, "Users are now successfuly subscribed.")
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong."

            if status_code == 403:
                msg = "You don't have the permission to do this."
            elif status_code == 404:
                msg = "The %s project does not exist." %  project

            return (status_code, msg)

    def reject(self, project, users):

        subscriptions = []
        for user in users:
            subscriptions.append((user, 'none'))

        try:
            self.pubsub.modify_subscriptions(self.pubsub_addr, project,
                    subscriptions=subscriptions)
            return (200, "Users are now successfuly rejected.")
        except IqError as e:
            status_code = int(e.iq['error']['code'])
            msg = "Something went wrong."

            if status_code == 403:
                msg = "You don't have the permission to do this."
            elif status_code == 404:
                msg = "The %s project does not exist." %  project

            return (status_code, msg)


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

