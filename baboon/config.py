import argparse
import logging
import logging.config

from ConfigParser import RawConfigParser

from common.config import Config
from logconf import LOGGING


SCMS = ('git',)


class ArgumentParser(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Baboon ! Ook !')

        subparsers = parser.add_subparsers()

        # Configure the quickstart parser.
        quickstart_parser = subparsers.add_parser('quickstart', help="start "
                                                  "the quickstart guide")
        quickstart_parser.set_defaults(which='quickstart')

        # Configure the register parser.
        register_parser = subparsers.add_parser('register', help="create an "
                                                "account.")
        register_parser.set_defaults(which='register')

        register_parser.add_argument('username', nargs='?', help="your "
                                     "username.")

        # Configure the projects parser.
        project_parser = subparsers.add_parser('projects', help="list all "
                                               "owned and subscribed "
                                               "projects.")
        project_parser.set_defaults(which='projects')

        project_parser.add_argument('project', help="the project name.")
        project_parser.add_argument('-a', '--all', action='store_true',
                                    help="display maximum information.")

        # Configure the create parser.
        create_parser = subparsers.add_parser('create', help="create a "
                                              "project.")
        create_parser.set_defaults(which='create')
        create_parser.add_argument('project', help="the project name.")
        create_parser.add_argument('-p', '--path', action='store',
                                   help="the project's path.")

        # Configure the delete parser.
        delete_parser = subparsers.add_parser('delete', help="delete a "
                                              "project.")
        delete_parser.set_defaults(which='delete')
        delete_parser.add_argument('project', help="the project name.")

        # Configure the join parser.
        join_parser = subparsers.add_parser('join', help="join a project.")
        join_parser.set_defaults(which='join')
        join_parser.add_argument('project', help="the project name.")
        join_parser.add_argument('-p', '--path', action='store',
                                   help="the project's path.")

        # Configure the unjoin parser.
        unjoin_parser = subparsers.add_parser('unjoin', help="unjoin a "
                                              "project.")
        unjoin_parser.set_defaults(which='unjoin')
        unjoin_parser.add_argument('project', help="the project name.")

        # Configure the accept parser.
        accept_parser = subparsers.add_parser('accept', help="accept a user "
                                              "to join a project.")
        accept_parser.set_defaults(which='accept')
        accept_parser.add_argument('project', help="the project name.")
        accept_parser.add_argument('username', help="the username to accept.")

        # Configure the reject parser.
        reject_parser = subparsers.add_parser('reject', help="kick a user "
                                              "from a project.")
        reject_parser.set_defaults(which='reject')
        reject_parser.add_argument('project', help="the project name.")
        reject_parser.add_argument('username', help="the username to reject.")

        # Configure the start parser.
        start_parser = subparsers.add_parser('start',
                                             help="start Baboon !")
        start_parser.set_defaults(which='start')
        start_parser.add_argument('--config', dest='configpath',
                                  help="override the default location of the "
                                  "config file")
        # logging args
        parser.add_argument('-d', '--debug', help="set logging to DEBUG",
                            action='store_const',
                            dest='loglevel',
                            const=logging.DEBUG,
                            default=logging.INFO)

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
        parser = RawConfigParser()
        parser.read(filename)

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
            self.attrs['server']['server'] = 'admin@baboon-project.org/baboond'


config = BaboonConfig(ArgumentParser(), LOGGING).attrs
