import os
import sys
import logging
import shutil

from baboon.baboon.monitor import Monitor
from baboon.baboon.transport import WatchTransport
from baboon.baboon.initializor import MetadirController
from baboon.baboon.transport import RegisterTransport, AdminTransport
from baboon.baboon.fmt import cinput, confirm_cinput, cwarn, csuccess, cerr

from baboon.baboon.config import check_user, check_server, check_project
from baboon.baboon.config import check_config, config, dump, SCMS
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException
from baboon.common.errors.baboon_exception import CommandException

logger = logging.getLogger(__name__)


def command(fn):
    def wrapped():
        try:
            return fn()
        except (BaboonException, CommandException) as err:
            cerr(err)
        except KeyboardInterrupt as err:
            print "Bye !"

    return wrapped


def start():
    """ Starts baboon client !
    """

    # Ensure the validity of the configuration file.
    check_config(add_mandatory_server_fields=['streamer', 'max_stanza_size'])

    metadirs = []
    monitor = None
    transport = None

    try:
        transport = _start_transport()
        monitor = _start_monitor()
        metadirs = _start_metadirs(monitor.handler.exclude)

        # Wait until the transport is disconnected before exiting Baboon.
        _wait_disconnect(transport)
    except BaboonException as err:
        logger.error(err)
    except KeyboardInterrupt:
        pass
    finally:
        _start_close(monitor, transport, metadirs)
        logger.info("Bye !")


@command
def register():
    """ Ask mandatory information and register the new user.
    """

    transport = None
    try:
        username = _get_username()
        passwd = _get_passwd()

        print("\nRegistration in progress...")

        # RegisterTransport uses the config attributes to register.
        config['user'] = {
            'jid': username,
            'passwd': passwd
        }

        # Registration...
        transport = RegisterTransport(callback=_on_register_finished)
        transport.open(block=True)
    finally:
        # Disconnect the transport if necessary.
        if transport and transport.connected.is_set():
            transport.close()
            transport.disconnected.wait(10)


@command
def projects():
    """ Lists all users in a project.
    """

    check_config()

    project = config['parser'].get('project')
    subs_by_project = []

    with AdminTransport(logger_enabled=False) as transport:
        # Get all subscriptions
        subscriptions = _projects_specific(transport, project) if project \
            else _projects_all(transport)

        # Display the subscriptions in a good format.
        _projects_print_users(subscriptions)


@command
def create():
    """ Create a new project with the project argument name.
    """

    check_server()
    check_user()

    project = config['parser']['project']
    path = config['parser']['path']
    project_scm = _check_scm(path)

    _check_project(project)
    config['projects'][project] = {
        'path': path,
        'scm': project_scm,
        'enable': 1
    }

    print("Creation in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.create_project(project)
        if not _on_action_finished(ret_status, msg):
            return

    dump()


@command
def delete():
    """ Delete the project with the project argument name.
    """

    check_config()

    project = config['parser']['project']
    print("Deletion in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.delete_project(project)
        _on_action_finished(ret_status, msg)

    project_path = _get_project_path(project)
    _delete_metadir(project, project_path)
    del config['projects'][project]
    dump()


@command
def join():
    """ Join the project with the project argument name.
    """

    check_server()
    check_user()

    project = config['parser']['project']
    path = config['parser']['path']
    project_scm = _check_scm(path)

    _check_project(project)
    config['projects'][project] = {
        'path': path,
        'scm': project_scm,
        'enable': 1
    }

    print("Join in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.join_project(project)
        if not _on_action_finished(ret_status, msg):
            return

    dump()


@command
def unjoin():
    """ Unjoin the project with the project argument name.
    """

    check_config()

    project = config['parser']['project']
    print("Unjoin in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.unjoin_project(project)
        _on_action_finished(ret_status, msg)

    project_path = _get_project_path(project)
    _delete_metadir(project, project_path)
    del config['projects'][project]
    dump()


@command
def accept():
    """ Accept the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = _get_username()

    print("Acceptation in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.accept_pending(project, username)
        _on_action_finished(ret_status, msg)


@command
def reject():
    """ Reject the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = _get_username()

    print("Rejection in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.reject(project, username)
        _on_action_finished(ret_status, msg)


@command
def kick():
    """ Kick the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = _get_username()

    print("Kick in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.kick(project, username)
        _on_action_finished(ret_status, msg)


@command
def init():
    """ Initialialize a new project.
    """

    check_config()

    project = config['parser']['project']
    project_path = _get_project_path(project)
    url = config['parser']['git-url']

    print("Initialize the project %s..." % project)
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.first_git_init(project, url)

        metadir_controller = MetadirController(project, project_path)
        metadir_controller.init_index()
        metadir_controller.create_baboon_index()
        metadir_controller.index.close()

        if not _on_action_finished(ret_status, msg):
            _delete_metadir(project, project_path)


def _start_transport():
    """ Builds and returns a new connected WatchTransport.
    """

    transport = WatchTransport()
    transport.open()
    transport.connected.wait()

    return transport


def _start_monitor():
    """ Builds and returns a new watched Monitor.
    """

    monitor = Monitor()
    monitor.watch()

    return monitor


def _start_metadirs(exclude=None):
    """ Builds and returns all metadirs. exclude is the exclude_method
    optionally needed by the MetadirController constructor.
    """

    metadirs = []
    for project, project_attrs in config['projects'].iteritems():
        # For each project, verify if the .baboon metadir is valid and
        # take some decisions about needed actions on the repository.
        metadir = MetadirController(project, project_attrs['path'], exclude)
        metadirs.append(metadir)
        metadir.go()

    return metadirs


def _start_close(monitor, transport, metadirs):
    """ Clears the monitor, transport and list of metadir before finishing the
    start command.
    """

    logger.info("Closing baboon...")

    # Close each metadir shelve index.
    for metadir in metadirs:
        metadir.index.close()

    # Close the transport and the monitor. If one of them is not
    # started, the close() method has no effect.
    if monitor:
        monitor.close()
    if transport:
        transport.close()
        transport.disconnected.wait(10)


def _wait_disconnect(transport, timeout=5):
    """ Polls the state of the transport's connection each `timeout` seconds.
    Exits when the transport is disconnected.
    """

    while not transport.disconnected.is_set():
        transport.disconnected.wait(timeout)


def _get_username():
    """ Returns the username by getting it from the config or asking it from
    stdin.
    """

    username = config['parser'].get('username')
    if not username:
        validations = [('^\w+$', 'Username can only contains alphanumeric and '
                        'underscore characters')]
        username = cinput('Username: ', validations=validations)

    # Transform the username to a JID.
    username += '@%s' % config['parser']['hostname']

    return username


def _get_passwd():
    """ Returns the password by getting it from stdin.
    """

    validations = [('^\w{6,}$', 'The password must be at least 6 characters '
                    'long.')]
    return confirm_cinput('Password: ', validations=validations, secret=True,
                          possible_err='The password must match !')


def _projects_specific(transport, project):
    """ Lists all users in a specific project. The transport must be connected.
    """

    project_users = transport.get_project_users(project) or []
    return [(project, project_users)]


def _projects_all(transport):
    """ Lists all users in a all projects. The transport must be connected.
    """

    subscriptions = []
    for project in config['projects']:
        subscriptions += _projects_specific(transport, project)

    return subscriptions


def _projects_print_users(subs_by_project):
    """ Prints the subs_by_project list of tuples.
    """

    for project, subs in subs_by_project:
        print("[%s]" % project)
        for sub in subs:
            print(" %s" % sub['jid'])


def _check_project(project_name):
    """ Checks if the project is not already defined in the configuration file.
    If so, raise a CommandException.
    """

    project = config['projects'].get(project_name)
    if project:
        if project.get('enable') == '0':
            raise CommandException(409, "The project is already defined in "
                                   "your configuration file, but it's "
                                   "disabled.")

        raise CommandException(409, "The project is already defined in your "
                               "configuration file.")


def _check_scm(path):
    """ Checks if the SCM in the path directory is supported. If not, raise a
    CommandException.
    """

    # Ensure the path exists.
    if not os.path.exists(path):
        raise CommandException(404, "The project's path does not exist on "
                               "your system.")

    # Ensure the path is a directory.
    if not os.path.isdir(path):
        raise CommandException(500, "The project's path is not a directory.")

    # Ensure the scm in the path directory exists and is supported.
    scm = _get_scm(path)
    if not scm:
        raise CommandException(500, "The project isn't managed by a supported "
                               "source code manager.")

    return scm


def _get_project_path(project_name):
    """ Returns the project path of the project_name. Raised a CommandException
    if cannot be retrieved.
    """

    try:
        project_path = config['projects'][project_name]['path']
        return project_path
    except KeyError:
        raise CommandException(404, "The project path cannot be found in your "
                               "configuration file.")


def _delete_metadir(project_name, project_path):
    """ Delete the metadir on the project_path. Raised a CommandException on
    error.
    """

    try:
        MetadirController(project_name, project_path).delete()
    except EnvironmentError:
        raise CommandException(500, "Cannot delete the metadir directory.")


def _on_register_finished(ret_status, msg, fatal=False):
    """ Callback for the registration.
    """

    _on_action_finished(ret_status, msg, fatal=fatal)
    # Dump the configuration file if there's no error.
    if ret_status == 200:
        dump()


def _on_action_finished(ret_status, msg, fatal=False):
    if ret_status >= 200 and ret_status < 300:
        csuccess(msg)
        return True
    else:
        # Print the error message.
        cerr(msg)
        return False


def _get_scm(path):
    """ Explores the path of the directory and returns the SCM used (one None).
    """

    for scm in SCMS:
        if os.path.isdir(os.path.join(path, '.%s' % scm)):
            return scm
