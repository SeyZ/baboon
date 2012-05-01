import os
import urllib
import urllib2
import json
import subprocess
import shlex
import sleekxmpp

from logger import logger
from config import Config


@logger
class Transport(sleekxmpp.ClientXMPP):
    """ The transport has the responsability to communicate via HTTP
    with the baboon server and to subscribe with XMPP 0060 with the
    Baboon XMPP server.
    """

    def __init__(self):
        """ Transport initializes all SleekXMPP stuff like plugins,
        events and more.
        """

        self.config = Config()
        self.logger.debug("Loaded baboon configuration")

        sleekxmpp.ClientXMPP.__init__(self, self.config.jid,
                                      self.config.password)
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

        # Instanciates a TransportUrl
        self.url = TransportUrl()

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

        opener = urllib2.build_opener(urllib2.HTTPHandler)

        data = {'project_name': self.config.node,
                'username': self.config.jid,
                'server_host': self.config.baboonsrv_host,
                }

        request = urllib2.Request(self.url.rsync_request(),
                                  data=urllib.urlencode(data))

        request.get_method = lambda: 'POST'
        result = opener.open(request)

        json_data = result.readline()
        return json.loads(json_data)

    def rsync(self):
        """ Starts a rsync transaction, rsync and stop the
        transaction.
        """

        # Starts the transaction
        trans_data = self.start_rsync_transaction()
        req_id = trans_data['req_id']
        remote_dir = trans_data['remote_dir']

        # Assumes that there's a rsync_key in the ~/.ssh/ folder.
        rsync_key_path = os.path.expanduser('~/.ssh/rsync_key')

        # Builds the rsync command
        rsync_cmd = 'rsync -ahv -e "ssh -i %s" %s/ %s' % \
            (rsync_key_path, self.config.path, remote_dir)

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

        opener = urllib2.build_opener(urllib2.HTTPHandler)
        request = urllib2.Request(self.url.rsync_request(req_id))
        request.get_method = lambda: 'DELETE'
        opener.open(request)

    def merge_verification(self):
        """ Calls baboon server in order to verify if there's a
        conflict or not.
        """

        opener = urllib2.build_opener(urllib2.HTTPHandler)
        data = {'project_name': self.config.node,
                'username': self.config.jid,
                }

        request = urllib2.Request(self.url.task(),
                                  data=urllib.urlencode(data))
        request.get_method = lambda: 'POST'
        opener.open(request)

    def _pubsub_event(self, msg):
        if msg['type'] in ('normal', 'headline'):
            self.logger.debug("Received pubsub item(s): \n%s" %
                              msg['pubsub_event'])

            items = msg['pubsub_event']['items']['substanzas']

            for item in items:
                self.logger.info(item['payload'].text)

        else:
            self.logger.debug("Received pubsub event: \n%s" %
                              msg['pubsub_event'])

from urlparse import urlunparse


class TransportUrl(object):

    TASK = 'tasks'
    RSYNC_REQUEST = '{0}/rsync_request'.format(TASK)

    def __init__(self):
        self.config = Config()

    def task(self):
        return self.make_url(self.TASK)

    def rsync_request(self, req_id=None):
        if req_id is None:
            return self.make_url(self.RSYNC_REQUEST)
        else:
            return self.make_url('%s/%s' % (self.RSYNC_REQUEST, req_id))

    def make_url(self, path):
        host = '%s:%s' % (self.config.baboonsrv_host,
                          self.config.baboonsrv_port)
        return urlunparse(('http', host, path, '', '', ''))
