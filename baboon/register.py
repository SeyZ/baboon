import os
import sys

from shutil import copy2

from transport import RegisterTransport, AdminTransport
from config import config
from common.logger import logger


@logger
class Register(object):
    """ The register class has the responsability to retrieve new user
    information through the RegisterCmd class and to create the new user
    through the RegisterTransport.
    """

    def __init__(self):
        """ When the Register class is instantiated, asks the inputs and
        creates the project.
        """

        # The fatal flag is used when an error needs to sys.exit() with a error
        # status code.
        self.fatal = False

        # The default configuration attributes.
        config.server = 'admin@baboon-project.org'
        config.pubsub = 'pubsub.baboon-project.org'

        # Instanciate the register command.
        register_cmd = RegisterCmd()

        # The command to execute.
        onecmd = 'register'

        # If the username is provided in the command line, append it to the
        # command.
        if config.username:
            onecmd += ' ' + config.username

        # Execute the register command and retrieve the username and the
        # password to use for the registration.
        config.jid, config.password = register_cmd.onecmd(onecmd)

        # Go registration ! The RegisterTransport use the config.jid and
        # config.password for the registration. The config object is a
        # singleton object.
        self.transport = RegisterTransport(callback=self._on_action_finished)
        self.transport.open(block=True)

        # Verifies if there's no fatal error at this point. If it's the case,
        # exit with the status code 1.
        if self.fatal:
            sys.exit(1)

        project = None

        create_project = cinput_yes_no('Would you like to create a project?')
        if create_project:
            # The user wants to create a project.
            project = register_cmd.onecmd('create_project')

            # Create the project.
            self.transport = AdminTransport(logger_enabled=False)
            self.transport.open()
            ret_status, msg = self.transport.create_project(project)
            self.transport.close()

            self._on_action_finished(ret_status, msg)
            if ret_status == 409:
                self._ask_join_project()

        else:
            project = self._ask_join_project()

        self.save_user_config(config.jid, config.password, project)

    def _on_action_finished(self, ret_status, msg, fatal=False):
        if ret_status >= 200 and ret_status < 300:
            csuccess(msg)
            return True
        else:
            # Print the error message.
            cerr(msg)

            # If the error is fatal, set the instance flag to True.
            if fatal:
                self.fatal = True

            return False

    def _ask_join_project(self, project=None):

        join = cinput_yes_no("Would you like to join an existing project ?")
        if join:
            if not project:
                project = cinput("Which project would you join ? ")

            self.transport = AdminTransport(logger_enabled=False)
            self.transport.open()
            status_code, msg = self.transport.join_project(project)
            self.transport.close()

            no_err = self._on_action_finished(status_code, msg)
            if no_err:
                return project

    def save_user_config(self, jid, password, project=None):

        if project:
            csuccess("Your registration is now fully configured.")
        else:
            cwarn("You are neither a project owner nor a project contributor. "
                    "Please, create one or join a project.")

        baboonrc_path = os.path.expanduser('~/.baboonrc')
        baboonrc_old_path = os.path.expanduser('~/.baboonrc.old')

        if os.path.exists(baboonrc_path):
            cwarn("A baboon configuration file already exists. Save it as "
                    "~/.baboonrc.old")
            copy2(baboonrc_path, baboonrc_old_path)

        csuccess("The new configuration file is written in ~/.baboonrc\n")

        with open(baboonrc_path, 'w') as f:
            f.write('[project]\n')
            f.write('pubsub=pubsub.baboon-project.org\n')
            f.write('server=admin@baboon-project.org\n')
            f.write('streamer=streamer.baboon-project.org\n')
            if project:
                f.write('node=%s\n' % project)
            f.write('jid=%s\n' % jid)
            f.write('password=%s\n' % password)
            f.write('scm=git\n')
            f.write('max_stanza_size=65536\n')

