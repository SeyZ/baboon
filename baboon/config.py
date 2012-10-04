import sys
import argparse
import logging
import logging.config

if sys.version_info < (3, 0):
    from ConfigParser import RawConfigParser, MissingSectionHeaderError
else:
    from configparser import RawConfigParser, MissingSectionHeaderError

from baboon.fmt import cerr
from baboon.logconf import LOGGING
from babooncommon.config import Config


SCMS = ('git',)


class ArgumentParser(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Baboon ! Ook !')

        subparsers = parser.add_subparsers()

        # Configure the REGISTER parser.
        register_parser = subparsers.add_parser('register', help="create an "
                                                "account.")
        register_parser.set_defaults(which='register')

        register_parser.add_argument('username', nargs='?', help="your "
                                     "username.")

        # Configure the PROJECTS parser.
        project_parser = subparsers.add_parser('projects', help="list all "
                                               "owned and subscribed "
                                               "projects.")
        project_parser.set_defaults(which='projects')

        project_parser.add_argument('project', help="the project name.")
        project_parser.add_argument('-a', '--all', action='store_true',
                                    help="display maximum information.")

        # Configure the CREATE parser.
        create_parser = subparsers.add_parser('create', help="create a "
                                              "project.")
        create_parser.set_defaults(which='create')
        create_parser.add_argument('project', help="the project name.")
        create_parser.add_argument('-p', '--path', action='store',
                                   help="the project's path.")

        # Configure the DELETE parser.
        delete_parser = subparsers.add_parser('delete', help="delete a "
                                              "project.")
        delete_parser.set_defaults(which='delete')
        delete_parser.add_argument('project', help="the project name.")

        # Configure the JOIN parser.
        join_parser = subparsers.add_parser('join', help="join a project.")
        join_parser.set_defaults(which='join')
        join_parser.add_argument('project', help="the project name.")
        join_parser.add_argument('-p', '--path', action='store',
                                 help="the project's path.")

        # Configure the UNJOIN parser.
        unjoin_parser = subparsers.add_parser('unjoin', help="unjoin a "
                                              "project.")
        unjoin_parser.set_defaults(which='unjoin')
        unjoin_parser.add_argument('project', help="the project name.")

        # Configure the ACCEPT parser.
        accept_parser = subparsers.add_parser('accept', help="accept a user "
                                              "to join a project.")
        accept_parser.set_defaults(which='accept')
        accept_parser.add_argument('project', help="the project name.")
        accept_parser.add_argument('username', help="the username to accept.")

        # Configure the REJECT parser.
        reject_parser = subparsers.add_parser('reject', help="kick a user "
                                              "from a project.")
        reject_parser.set_defaults(which='reject')
        reject_parser.add_argument('project', help="the project name.")
        reject_parser.add_argument('username', help="the username to reject.")

        # Configure the KICK parser.
        reject_parser = subparsers.add_parser('kick', help="kick a user "
                                              "from a project.")
        reject_parser.set_defaults(which='kick')
        reject_parser.add_argument('project', help="the project name.")
        reject_parser.add_argument('username', help="the username to kick.")

        # Configure the INIT parser.
        init_parser = subparsers.add_parser('init', help="initialize a new "
                                             "project.")
        init_parser.set_defaults(which='init')
        init_parser.add_argument('project', help="the project name.")
        init_parser.add_argument('git-url', help="specify the git url to "
                                 "fetch in order to initialize the project.")

        # Configure the START parser.
        start_parser = subparsers.add_parser('start', help="start Baboon !")
        start_parser.set_defaults(which='start')
        start_parser.add_argument('--no-init', dest='init',
                                  default=False, action='store_true',
                                  help="avoid to execute initial rsync")

        # logging args
        parser.add_argument('-d', '--debug', help="set logging to DEBUG",
                            action='store_const',
                            dest='loglevel',
                            const=logging.DEBUG,
                            default=logging.INFO)
        parser.add_argument('--config', dest='configpath',
                            help="override the default location of the "
                            "config file")

        # Add the nosave option to some of the parsers.
        no_save_subparsers = (register_parser, create_parser, delete_parser,
                              join_parser, unjoin_parser)

        for subparser in no_save_subparsers:
            subparser.add_argument('--nosave', action='store_true',
                                   dest='nosave', default=False,
                                   help="don't overwrite config file")

        self.args = parser.parse_args()


class BaboonConfig(Config):

    def __init__(self, arg_parser, logconf):
        super(BaboonConfig, self).__init__(ArgumentParser(), LOGGING)

    def _init_config_file(self):
        """ Override the initialization of the configuration file. Here's we
        parse the configuration file and we transform all sections in dict into
        self.attrs except for the projects. The projects are put in the
        'projects' key.

        example:
            self.attrs['user']['jid'] => chuck.norris@baboon-project.org
            self.attrs['projects']['linux_kernel'] => {path: ~/workspace/linux}
        """

        known_section = ('user', 'server')
        self.attrs['projects'] = {}

        filename = self._get_config_path()
        # Check if we found a location for the config file
        # If not, let's go brutal.
        if not filename:
            cerr("Configuration file not found. Quitting.")
            sys.exit(1)

        # Parse the file if found.
        # Check if it looks like a real python config file.
        parser = RawConfigParser()
        try:
            parser.read(filename)
        except MissingSectionHeaderError:
            cerr("Config file not properly formatted. %s" % filename)
            sys.exit(1)

        # Fill the config dict whit what we found in the config file
        for section in parser.sections():
            if section in known_section:
                self.attrs[section] = dict(parser.items(section))
            else:
                # The current section in the name of a project.
                self.attrs['projects'][section] = dict(parser.items(section))

        # I highly doubt this portion of code :)
        # Some hardcoded server values, if we've found an empty server section.
        # Shouldn't happen.
        if not self.attrs.get('server'):
            self.attrs['server'] = {}
            self.attrs['server']['max_stanza_size'] = 65535
            self.attrs['server']['pubsub'] = 'pubsub.baboon-project.org'
            self.attrs['server']['streamer'] = 'streamer.baboon-project.org'
            self.attrs['server']['master'] = 'admin@baboon-project.org/baboond'


config = BaboonConfig(ArgumentParser(), LOGGING).attrs
