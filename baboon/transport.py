import os
import subprocess
import shlex
import sleekxmpp

from config import config
from common.stanza.rsync import RsyncStart, RsyncStop, MergeVerification
from common.logger import logger
from common.errors.baboon_exception import BaboonException


@logger
class Transport(sleekxmpp.ClientXMPP):
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

        sleekxmpp.ClientXMPP.__init__(self, config.jid, config.password)
        self.logger.debug("Configured SleekXMPP library")

        # Register plugins
        self.register_plugin('xep_0060')  # PubSub

        # Register events
        self.add_event_handler("session_start", self.start)
        self.logger.debug("Listening 'session_start' sleekxmpp event")

        self.register_handler(
            sleekxmpp.xmlstream.handler.Callback(
                'Pubsub event',
                sleekxmpp.xmlstream.matcher.StanzaPath(
                    'message/pubsub_event'),
                self._pubsub_event))
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

        # register the pubsub plugin
        self.pubsub = self.plugin["xep_0060"]

        self.logger.info('Connected')

    def close(self):
        """ Closes the XMPP connection.
        """

        self.disconnect()
        self.logger.debug('Closed the XMPP connection')

    def start_rsync_transaction(self):
        """ Starts a rsync transaction and return its id.
        """

        msg = RsyncStart()
        msg['node'] = config.node
        msg['username'] = config.jid

        iq = self.make_iq_set(
            ifrom=config.jid,
            ito='admin@baboon-project.org/baboond',
            sub=msg)

        # TODO: catch the possible exception
        try:
            raw_ret = iq.send()
            return raw_ret['rsync_ok'].values
        except sleekxmpp.exceptions.IqError, e:
            raise BaboonException(e.iq['error']['condition'])

    def rsync(self):
        """ Starts a rsync transaction, rsync and stop the
        transaction.

        Raises a BaboonException if there's a problem.
        """

        # Starts the transaction
        trans_data = self.start_rsync_transaction()
        req_id = trans_data['req_id']
        remote_dir = trans_data['remote_dir']

        # Assumes that there's a rsync_key in the ~/.ssh/ folder.
        rsync_key_path = os.path.expanduser('~/.ssh/rsync_key')

        # Builds the rsync command
        rsync_cmd = 'rsync -ahv -e "ssh -i %s" %s/ %s' % \
            (rsync_key_path, config.path, remote_dir)

        self.logger.info('Sync...')

        args = shlex.split(str(rsync_cmd))  # make sure that rsync_cmd
                                            # is not unicoded

        # Go rsync
        proc = subprocess.Popen(args,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                shell=False)
        proc.communicate()

        self.logger.info('Sync finished')

        # Stops the transaction
        self.stop_rsync_transaction(req_id)

    def stop_rsync_transaction(self, req_id):
        """ Stops the rsync transaction identified by req_id.
        """

        msg = RsyncStop()
        msg['node'] = config.node
        msg['req_id'] = req_id

        iq = self.make_iq_set(
            ifrom=config.jid,
            ito='admin@baboon-project.org/baboond',
            sub=msg)

        # TODO: catch the possible exception
        iq.send()

    def merge_verification(self):
        """ Calls baboon server in order to verify if there's a
        conflict or not.
        """

        msg = MergeVerification()
        msg['node'] = config.node
        msg['username'] = config.jid

        iq = self.make_iq_set(
            ifrom=config.jid,
            ito='admin@baboon-project.org/baboond',
            sub=msg)

        # TODO: catch the possible exception
        iq.send()

    def _pubsub_event(self, msg):
        if msg['type'] in ('normal', 'headline'):
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            items = msg['pubsub_event']['items']['substanzas']

            for item in items:
                self.logger.info(item['payload'].get('status'))

        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])
