import os
import sys
import signal

from plugins import *
from config import config
from commands import commands
from transport import WatchTransport
from initializor import MetadirController
from monitor import Monitor
from common.logger import logger
from common.errors.baboon_exception import BaboonException


@logger
class Main(object):

    def __init__(self):

        # Exit baboon when receiving a sigint signal.
        signal.signal(signal.SIGINT, self.sigint_handler)

        self.metadirs = []

        self.which = config['parser']['which']

        # The start command is a special command. Call it from this class
        if self.which == 'start':
            if self.check_config():
                self.start()

        # Call the correct method according to the current arg subparser.
        elif hasattr(commands, self.which):
            if self.which != 'register':
                if self.check_user_config():
                    getattr(commands, self.which)()
                else:
                    self.logger.error("Missing user credentials in the"
                                      " configuration file.")
            else:
                getattr(commands, 'register')()

        # Wait until the transport is disconnected before exiting Baboon.
        if hasattr(self, 'transport'):
            while not self.transport.disconnected.is_set():
                self.transport.disconnected.wait(5)

        self.sigint_handler()

    def check_user_config(self):
        """
        """

        try:
            return '' not in (config['user']['jid'], config['user']['passwd'])
        except KeyError:
            return False


    def check_config(self):
        """Some sections and options of the config file are mandatory. Let's be
        sure they are at least filled. We leave the "filled correctly" to the
        XMPP server.
        """

        success = True
        hint = "An option misses its value"
        # First, check SERVER and USER sections
        try:
            # Of course, values can't be empty
            success = '' not in (config['server']['master'],
                                 config['server']['pubsub'],
                                 config['user']['jid'],
                                 config['user']['passwd'])

        # And some options are mandatory, else it fails
        except KeyError as err:
            success = False
            hint = err

        if not success:
            msg = ("Something's missing in your configuration file. "
                   "Hint: %s") % hint
            self.logger.error(msg)
            return success

        # Let's check that at least 1 project is set up
        # For each set up project, some options are mandatory and cannot be
        # empty.
        if len(config.get('projects', {})):
            for project in config['projects']:
                try:
                    success = '' not in (config['projects'][project]['path'],
                                         config['projects'][project]['scm'])

                    # Give a hint to the user. We're so kind.
                    if not success:
                        msg = ("Something's missing in your "
                               "configuration file. "
                               "Hint: %s in [%s]" % (hint, project))
                        self.logger.error(msg)
                        return success

                except KeyError as err:
                    success = False
                    hint = str(err)
                    hint += " not present for the '%s' project" % project
        else:
            success = False
            hint = "No project is configured."

        return success

    def start(self):
        self.monitor = None

        try:
            self.transport = WatchTransport()
            self.transport.open()

            self.monitor = Monitor(self.transport)
            self.monitor.watch()

            for project, project_attrs in config['projects'].iteritems():

                project_path = os.path.expanduser(project_attrs['path'])

                # For each project, verify if the .baboon metadir is valid and
                # take some decisions about needed actions on the repository.
                metadir = MetadirController(project, project_path,
                                            self.monitor.handler.exclude)
                self.metadirs.append(metadir)
                metadir.go()

        except BaboonException as err:
            sys.stderr.write("%s\n" % err)
            # Try to close the transport properly. If the transport is
            # not correctly started, the close() method has no effect.
            self.transport.close()

            # Same thing for the monitor
            if self.monitor:
                self.monitor.close()

            # Exits with a fail return code
            sys.exit(1)

    def sigint_handler(self, signal=None, frame=None):
        """ Handler method for the SIGINT signal.
        XMPP connection and service monitoring are correctly closed.
        Closing baboon in a clean way.
        """
        self.logger.debug("Received SIGINT signal")

        try:
            for metadir in self.metadirs:
                metadir.index.close()

            self.transport.close()
            self.monitor.close()
        except AttributeError:
            # If AttributeError is raise, transport or monitor does not exist.
            # It's not a problem.
            pass

        self.logger.info("Bye !")
        sys.exit(0)
