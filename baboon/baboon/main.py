import os
import sys
import signal

from baboon.common.errors.baboon_exception import ConfigException

# The config can raise a ConfigException if there's a problem.
try:
    from baboon.baboon.config import config
    from baboon.baboon.config import check_server, check_user, check_project
except ConfigException as err:
    # An error as occured while loading the global baboon configuration. So,
    # there's no logger correctly configured. Load a basic logger to print the
    # error message.
    import logging

    logging.basicConfig(format='%(message)s')
    logger = logging.getLogger(__name__)
    logger.error(err)

    sys.exit(1)

from baboon.baboon import commands
from baboon.baboon.plugins import *
from baboon.baboon.transport import WatchTransport
from baboon.baboon.initializor import MetadirController
from baboon.baboon.monitor import Monitor
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


@logger
class Main(object):

    def __init__(self):

        # Exit baboon when receiving a sigint signal.
        signal.signal(signal.SIGINT, self.sigint_handler)

        self.metadirs = []

        self.which = config['parser']['which']

        try:
            # The start command is a special command. Call it from this class
            if self.which == 'start':
                self.start()
            # Call the correct method according to the current arg subparser.
            elif hasattr(commands, self.which):
                getattr(commands, self.which)()
        except ConfigException as err:
            self.logger.error(err)

        # Wait until the transport is disconnected before exiting Baboon.
        if hasattr(self, 'transport'):
            while not self.transport.disconnected.is_set():
                self.transport.disconnected.wait(5)

    def start(self):
        check_server(add_mandatory_fields=['streamer'])
        check_user()
        check_project()

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

            self.monitor.close()
            self.transport.close()
        except AttributeError:
            # If AttributeError is raise, transport or monitor does not exist.
            # It's not a problem.
            pass

        self.logger.info("Bye !")
        sys.exit(0)
