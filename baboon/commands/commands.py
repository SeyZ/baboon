import os
import shutil

from baboon.transport import RegisterTransport, AdminTransport
from baboon.fmt import cinput, confirm_cinput, cwarn
from baboon.fmt import csuccess, cerr
from baboon.config import config
from common.errors.baboon_exception import CommandException


def register():
    """ Ask mandatory information and register the new user.
    """

    transport = None
    username = config['parser'].get('username')
    passwd = None

    try:
        # Ask the user from stdin if username is None or empty.
        if not username:
            username = cinput('Username: ', validations=[('^\w+$', 'Username '
            'can only contains alphanumeric and underscore characters')])

        # Transform the username to a baboon-project JID.
        username += '@baboon-project.org'

        # Get the password from stdin.
        passwd = confirm_cinput('Password: ', validations=[('^\w{6,}$', 'The '
               'password must be at least 6 characters long.')], secret=True,
                possible_err='The password must match !')

        print "\nRegistration in progress..."

        # RegisterTransport uses the config attributes to register.
        config['user']['jid'] = username
        config['user']['passwd'] = passwd

        # Registration...
        transport = RegisterTransport(callback=_on_action_finished)
        transport.open(block=True)

        # Persist register information in the user configuration file.
        save_user_config()

    except CommandException:
        pass
    except KeyboardInterrupt:
        print "\nBye !"
    finally:
        # Check if the transport exists and if its connected.
        if transport and transport.connected.is_set():
            transport.close()


def projects():

    project = config['parser']['project']
    subscriptions = []

    with AdminTransport(logger_enabled=False) as transport:
        subscriptions = transport.get_project_users(project) or []

    for subscription in subscriptions:
        print "%s" % subscription['jid']


def create():
    """ Create a new project with the project argument name.
    """

    project = config['parser']['project']

    print "Creation in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.create_project(project)
        _on_action_finished(ret_status, msg)

        # TODO: write the new project into the config file.


def delete():
    """ Delete the project with the project argument name.
    """

    project = config['parser']['project']

    print "Deletion in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.delete_project(project)
        _on_action_finished(ret_status, msg)

        # TODO: delete the project into the config file.


def join():
    """ Join the project with the project argument name.
    """

    project = config['parser']['project']

    print "Join in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.join_project(project)
        return _on_action_finished(ret_status, msg)

        # TODO: write the joined project into the config file.

def unjoin():
    """ Unjoin the project with the project argument name.
    """

    project = config['parser']['project']

    print "Unjoin in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.unjoin_project(project)
        return _on_action_finished(ret_status, msg)

        # TODO: write the joined project into the config file.

def accept():
    """ Accept the username to the project.
    """

    project = config['parser']['project']
    username = config['parser']['username']

    print "Acceptation in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.accept_pending(project, [username])
        return _on_action_finished(ret_status, msg)


def reject():
    """ Reject the username to the project.
    """

    project = config['parser']['project']
    username = config['parser']['username']

    print "Rejection in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.reject(project, [username])
        return _on_action_finished(ret_status, msg)


def _on_action_finished(ret_status, msg, fatal=False):
    if ret_status >= 200 and ret_status < 300:
        csuccess(msg)
        return True
    else:
        # Print the error message.
        cerr(msg)
        return False

def save_user_config(project=None):

    baboonrc_path = os.path.expanduser('~/.baboonrc')
    baboonrc_old_path = os.path.expanduser('~/.baboonrc.old')

    if os.path.exists(baboonrc_path):
        cwarn("A baboon configuration file already exists. Save it as "
                "~/.baboonrc.old")
        shutil.copy2(baboonrc_path, baboonrc_old_path)

    csuccess("The new configuration file is written in ~/.baboonrc\n")
    return

    with open(baboonrc_path, 'w') as f:
        f.write('[project]\n')
        f.write('pubsub=pubsub.baboon-project.org\n')
        f.write('server=admin@baboon-project.org\n')
        f.write('streamer=streamer.baboon-project.org\n')
        if project:
            f.write('node=%s\n' % project)
        f.write('jid=%s\n' % config['user']['jid'])
        f.write('password=%s\n' % config['user']['password'])
        f.write('scm=git\n')
        f.write('max_stanza_size=65536\n')

