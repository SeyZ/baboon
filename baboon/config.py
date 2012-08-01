import os
import argparse
import logging
import logging.config

from common.config import Config
from logconf import LOGGING


class ArgumentParser(object):
    def __init__(self):
        parser = argparse.ArgumentParser(description='Baboon ! Ook !')

        subparsers = parser.add_subparsers()

        # Configure the quickstart parser.
        quickstart_parser = subparsers.add_parser('quickstart',
                help="start the quickstart guide")
        quickstart_parser.set_defaults(which='quickstart')

        # Configure the register parser.
        register_parser = subparsers.add_parser('register', help="create an "
                "account.")
        register_parser.set_defaults(which='register')

        register_parser.add_argument('username', nargs='?', help="your "
                "username.")

        # Configure the projects parser.
        project_parser = subparsers.add_parser('projects', help="list all "
                "owned and subscribed projects.")
        project_parser.set_defaults(which='projects')

        project_parser.add_argument('project', help="the project name.")
        project_parser.add_argument('-a', '--all', action='store_true',
                help="display maximum information.")

        # Configure the create parser.
        create_parser = subparsers.add_parser('create', help="create a "
                "project.")
        create_parser.set_defaults(which='create')
        create_parser.add_argument('project', help="the project name.")

        # Configure the delete parser.
        delete_parser = subparsers.add_parser('delete', help="delete a "
                "project.")
        delete_parser.set_defaults(which='delete')
        delete_parser.add_argument('project', help="the project name.")

        # Configure the join parser.
        join_parser = subparsers.add_parser('join', help='join a project.')
        join_parser.set_defaults(which='join')
        join_parser.add_argument('project', help="the project name.")

        # Configure the unjoin parser.
        unjoin_parser = subparsers.add_parser('unjoin', help='unjoin a project.')
        unjoin_parser.set_defaults(which='unjoin')
        unjoin_parser.add_argument('project', help="the project name.")

        # Configure the accept parser.
        accept_parser = subparsers.add_parser('accept', help='accept a user '
                'to join a project.')
        accept_parser.set_defaults(which='accept')
        accept_parser.add_argument('project', help="the project name.")
        accept_parser.add_argument('username', help="the username to accept.")

        # Configure the reject parser.
        reject_parser = subparsers.add_parser('reject', help='kick a user '
                'from a project.')
        reject_parser.set_defaults(which='reject')
        reject_parser.add_argument('project', help="the project name.")
        reject_parser.add_argument('username', help="the username to reject.")

        # Configure the start parser.
        start_parser = subparsers.add_parser('start',
                                             help="start Baboon !")
        start_parser.set_defaults(which='start')
        start_parser.add_argument('-p', '--path', dest='path',
                default=os.getcwd(), help="specify the project directory")
        start_parser.add_argument('--config', dest='configpath',
                help="override the default location of the config file")
        # logging args
        parser.add_argument('-d', '--debug', help="set logging to DEBUG",
                            action='store_const',
                            dest='loglevel',
                            const=logging.DEBUG,
                            default=logging.INFO)

        self.args = parser.parse_args()

config = Config(ArgumentParser(), LOGGING).attrs
