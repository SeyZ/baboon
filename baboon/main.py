import sys
import signal

from plugins import *
from config import config
from commands import commands
from transport import WatchTransport
from monitor import Monitor
from common.logger import logger
from common.errors.baboon_exception import BaboonException


@logger
class Main(object):

    def __init__(self):
        self.monitor = None

        self.which = config['parser']['which']

        # The start command is a special command. Call it from this class
        if self.which == 'start':
            if self.check_config():
                self.start()
            return

        # Call the correct method according to the current arg subparser.
        if hasattr(commands, self.which):
            getattr(commands, self.which)()

    def check_config(self):
        """Some sections and options of the config file are mandatory. Let's be
        sure they are at least filled. We leave the "filled correctly" to the
        XMPP server.
        """

        success = True
        hint = "An option misses its value."
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

        # Let's check at least 1 project is set up
        # For each set up project, some options are mandatory and cannot be
        # empty.
        if len(config.get('projects', {})):
            for project in config['projects']:
                try:
                    success = '' not in (config['projects'][project]['path'],
                                         config['projects'][project]['scm'])
                except KeyError as err:
                    success = False
                    hint = str(err)
                    hint += " not present for the '%s' project" % project
        else:
            success = False
            hint = "No project is configured."

        # Give a hint to the user. We're so kind.
        if not success:
            msg = "Something's missing in your configuration file. "
            "I can't start. Hint: %s" % hint
            self.logger.error(msg)

        return success

    def start(self):
        try:
            # exists baboon when receiving a sigint signal
            signal.signal(signal.SIGINT, self.sigint_handler)

            self.transport = WatchTransport()
            self.transport.open()

            self.monitor = Monitor(self.transport)
            self.monitor.watch()

            # TODO this won't work on windows...
            signal.pause()

        except BaboonException, err:
            sys.stderr.write("%s\n" % err)
            # Try to close the transport properly. If the transport is
            # not correctly started, the close() method has no effect.
            self.transport.close()

            # Same thing for the monitor
            if self.monitor:
                self.monitor.close()

            # Exits with a fail return code
            sys.exit(1)

    def sigint_handler(self, signal, frame):
        """ Handler method for the SIGINT signal.
        XMPP connection and service monitoring are correctly closed.
        Closing baboon in a clean way.
        """
        self.logger.debug("Received SIGINT signal")
        self.transport.close()
        self.monitor.close()

        self.logger.info("Bye !")
        sys.exit(0)
