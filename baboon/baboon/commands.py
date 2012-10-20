import os
import sys
import logging
import shutil

from baboon.baboon.monitor import Monitor
from baboon.baboon.transport import WatchTransport
from baboon.baboon.initializor import MetadirController
from baboon.baboon.transport import RegisterTransport, AdminTransport
from baboon.baboon.fmt import cinput, confirm_cinput, cwarn, csuccess, cerr

from baboon.baboon.config import check_config, config, dump, SCMS
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException
from baboon.common.errors.baboon_exception import CommandException

logger = logging.getLogger(__name__)


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
        _start_close(monitor, transport, metadirs)
        sys.exit(1)
    except KeyboardInterrupt:
        _start_close(monitor, transport, metadirs)
        logger.info("Bye !")


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
        username += '@%s' % config['parser']['hostname']

        # Get the password from stdin.
        passwd = confirm_cinput('Password: ', validations=[('^\w{6,}$', 'The '
               'password must be at least 6 characters long.')], secret=True,
                possible_err='The password must match !')

        print("\nRegistration in progress...")

        # RegisterTransport uses the config attributes to register.
        config['user'] = {
            'jid': username,
            'passwd': passwd
        }

        # Registration...
        transport = RegisterTransport(callback=_on_action_finished)
        transport.open(block=True)

        # Persist register information in the user configuration file.
        if not config['parser']['nosave']:
            dump()

    except CommandException:
        pass
    except KeyboardInterrupt:
        print("\nBye !")
    finally:
        # Check if the transport exists and if its connected.
        if transport and transport.connected.is_set():
            transport.close()


def projects():

    check_config()

    project = config['parser']['project']
    subscriptions = []

    with AdminTransport(logger_enabled=False) as transport:
        subscriptions = transport.get_project_users(project) or []

    for subscription in subscriptions:
        print("%s" % subscription['jid'])


def create():
    """ Create a new project with the project argument name.
    """

    check_server()
    check_user()

    project = config['parser']['project']
    path = config['parser'].get('path')
    if not path and not config['parser']['nosave']:
        cerr("Please specify the project's path on your system with the "
             "'--path' option.")
        return

    print("Creation in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.create_project(project)
        success = _on_action_finished(ret_status, msg)
        if not success:
            return success

    # Check if path exists on the system
    project_scm = ''
    if os.path.isdir(path):
        project_scm = _guess_scm(path)
    else:
        cwarn("The project's path does not exist on your system.")

    if config['projects'].get(project):
        cwarn("The project was already defined in your configuration file")
        config['projects'][project]['enable'] = 1
    else:
        config['projects'][project] = {}
        config['projects'][project]['path'] = path
        config['projects'][project]['scm'] = project_scm
        config['projects'][project]['enable'] = 1

    if not config['parser']['nosave']:
        dump()
    return success


def delete():
    """ Delete the project with the project argument name.
    """

    check_config()

    project = config['parser']['project']

    print("Deletion in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.delete_project(project)
        success = _on_action_finished(ret_status, msg)
        if not success:
            return success

    try:
        # Delete the metadir directory.
        project_path = config['projects'][project]['path']
        MetadirController(project, project_path).delete()

        # Delete the project entry in the configuration dict.
        del config['projects'][project]

        # Dump the configuration dict.
        if not config['parser']['nosave']:
            dump()
    except KeyError:
        # The project entry does not exist in the configuration file
        cwarn("The project was not found in your configuration file")
    except OSError:
        cwarn("Cannot delete the .baboon directory.")

    return success


def join():
    """ Join the project with the project argument name.
    """

    check_config()

    project = config['parser']['project']
    path = config['parser'].get('path')
    if not path:
        cerr("Please specify the project's path on your system with the "
             "'--path' option.")
        return

    project_scm = ''

    print("Join in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.join_project(project)
        success = _on_action_finished(ret_status, msg)
        #if not success:
        #    return success

    # Check if path exists on the system
    if os.path.isdir(path):
        project_scm = _guess_scm(path)
    else:
        cwarn("The project's path does not exist on your system.")

    if success:
        if config['projects'].get(project):
            cwarn("The project was already defined in your configuration file")
            config['projects'][project]['enable'] = 1
        else:
            config['projects'][project] = {}
            config['projects'][project]['path'] = path
            config['projects'][project]['scm'] = project_scm
            config['projects'][project]['enable'] = 1

        if not config['parser']['nosave']:
            dump()

    return success


def unjoin():
    """ Unjoin the project with the project argument name.
    """

    check_config()

    project = config['parser']['project']

    print("Unjoin in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.unjoin_project(project)
        success = _on_action_finished(ret_status, msg)

    if config['projects'].get(project):
        config['projects'][project]['enable'] = 0
    else:
        cwarn("The project was not defined in your configuration file")

    if not config['parser']['nosave']:
        dump()
    return success


def accept():
    """ Accept the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = config['parser']['username']

    print("Acceptation in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.accept_pending(project, username)
        return _on_action_finished(ret_status, msg)


def reject():
    """ Reject the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = config['parser']['username']

    print("Rejection in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.reject(project, username)
        return _on_action_finished(ret_status, msg)


def kick():
    """ Kick the username to the project.
    """

    check_config()

    project = config['parser']['project']
    username = config['parser']['username']

    print("Kick in progress...")
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.kick(project, username)
        return _on_action_finished(ret_status, msg)


def init():
    """ Initialialize a new project.
    """

    check_config()

    project = config['parser']['project']

    project_path = None
    try:
        project_path = config['projects'][project]['path']
    except KeyError:
        cerr("Failed to find the %s project in the configuration file." %
             project)
        sys.exit(1)

    url = config['parser']['git-url']

    print("Initialize the project %s..." % project)
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.first_git_init(project, url)

        metadir_controller = MetadirController(project, project_path)
        metadir_controller.init_index()
        metadir_controller.create_baboon_index()
        metadir_controller.index.close()

        state = _on_action_finished(ret_status, msg)
        if not state:
            # On error, remove the metadir directory.
            metadir_controller.delete()

        return state


def _on_action_finished(ret_status, msg, fatal=False):
    if ret_status >= 200 and ret_status < 300:
        csuccess(msg)
        return True
    else:
        # Print the error message.
        cerr(msg)
        return False


def _guess_scm(path):
    """Rough guess of the source code manager the user uses for the project
    based on the path he provides in the command line. For instance, it checks
    if a .git folder is present in the project's folder. SCMs are defined in
    the baboon/config.py file.
    """
    project_scm = ''
    # Detect scm in path
    for scm in SCMS:
        if os.path.isdir(os.path.join(path, '.' + scm)):
            project_scm = scm
    if not project_scm:
        cwarn("Your project isn't managed by a supported source code manager.")

    return project_scm
