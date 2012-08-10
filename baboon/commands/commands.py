import os
import shutil

from baboon.transport import RegisterTransport, AdminTransport
from baboon.fmt import cinput, confirm_cinput, cwarn
from baboon.fmt import csuccess, cerr

from baboon.config import config, SCMS
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
        config['user'] = {
            'jid': username,
            'passwd': passwd
        }

        # Registration...
        transport = RegisterTransport(callback=_on_action_finished)
        transport.open(block=True)

        # Persist register information in the user configuration file.
        if config['parser']['save']:
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
    path = config['parser'].get('path')
    if not path:
        cerr("Please specify the project's path on your system with the "
             "'--path' option.")
        return

    print "Creation in progress..."
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

    if config['parser']['save']:
        save_user_config()
    return success


def delete():
    """ Delete the project with the project argument name.
    """

    project = config['parser']['project']

    print "Deletion in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.delete_project(project)
        success = _on_action_finished(ret_status, msg)
        if not success:
            return success

    try:
        del config['projects'][project]
    except AttributeError:
        cwarn("The project was not found in your configuration file")

    if config['parser']['save']:
        save_user_config()
    return success


def join():
    """ Join the project with the project argument name.
    """

    project = config['parser']['project']
    path = config['parser'].get('path')
    if not path:
        cerr("Please specify the project's path on your system with the "
             "'--path' option.")
        return

    project_scm = ''

    print "Join in progress..."
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

    if config['projects'].get(project):
        cwarn("The project was already defined in your configuration file")
        config['projects'][project]['enable'] = 1
    else:
        config['projects'][project] = {}
        config['projects'][project]['path'] = path
        config['projects'][project]['scm'] = project_scm
        config['projects'][project]['enable'] = 1

    if config['parser']['save']:
        save_user_config()
    return success


def unjoin():
    """ Unjoin the project with the project argument name.
    """

    project = config['parser']['project']

    print "Unjoin in progress..."
    with AdminTransport(logger_enabled=False) as transport:
        ret_status, msg = transport.unjoin_project(project)
        success = _on_action_finished(ret_status, msg)

    if config['projects'].get(project):
        config['projects'][project]['enable'] = 0
    else:
        cwarn("The project was not defined in your configuration file")

    if config['parser']['save']:
        save_user_config()
    return success


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


def save_user_config():
    """Saves the config dict to the user's configuration file ~/.baboonrc.
    If the file already exists, it's copied to ~/.baboonrc.old and the original
    file is overwritten.
    """
    baboonrc_path = os.path.expanduser('~/.baboonrc')
    baboonrc_old_path = os.path.expanduser('~/.baboonrc.old')

    if os.path.exists(baboonrc_path):
        cwarn("A baboon configuration file already exists. Saved it as "
                "~/.baboonrc.old")
        shutil.copy2(baboonrc_path, baboonrc_old_path)

    csuccess("The new configuration file is written in ~/.baboonrc\n")
    filecontent = ''

    # Add the server section
    filecontent += '[server]\n'
    for option, value in config['server'].iteritems():
        filecontent += '%s = %s\n' % (option, value)
    filecontent += '\n'

    # Add the user section
    filecontent += '[user]\n'
    for option, value in config['user'].iteritems():
        filecontent += '%s = %s\n' % (option, value)
    filecontent += '\n'

    # Add projects
    for project, project_options in config['projects'].iteritems():
        filecontent += '[%s]\n' % project
        for option, value in project_options.iteritems():
            filecontent += '%s = %s\n' % (option, value)
        filecontent += '\n'

    # Example of project
    filecontent += """# Example of project definition
#[awesome_project] \t# The project name on the baboon server
#path = /pathto/project # The project path of your system
#scm = git \t\t# The source code manager you use for this project
#enable = 1 \t\t# You want baboon to actually watch this project
"""

    # Write content to file
    with open(baboonrc_path, 'w') as fd:
        fd.write(filecontent)


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
