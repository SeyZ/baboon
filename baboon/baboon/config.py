import os
import shutil
import sys
import argparse
import logging
import logging.config

if sys.version_info < (3, 0):
    from ConfigParser import RawConfigParser, MissingSectionHeaderError
else:
    from configparser import RawConfigParser, MissingSectionHeaderError

from baboon.baboon.fmt import cerr, cwarn, csuccess
from baboon.baboon.dictconf import LOGGING, PARSER
from baboon.common.config import get_config_args, get_config_file
from baboon.common.config import init_config_log
from baboon.common.errors.baboon_exception import ConfigException

SCMS = ('git',)


def check_server(add_mandatory_fields=[]):
    """ Checks the server section in the config dict. The add_mandatory_fields
    list allows to add more mandatory fields.
    """

    mandatory_keys = set(['master', 'pubsub'] + add_mandatory_fields)
    _check_config_section('server', mandatory_keys)


def check_user(add_mandatory_fields=[]):
    """ Checks the user section in the config dict. The add_mandatory_fields
    list allows to add more mandatory fields.
    """

    mandatory_keys = set(['jid', 'passwd'] + add_mandatory_fields)
    _check_config_section('user', mandatory_keys)


def check_project(add_mandatory_fields=[]):
    """ Checks if there's at least one configured project. The
    add_mandatory_fields list allows to add more mandatory fields to validate
    all configured projects.
    """

    mandatory_keys = set(['path', 'scm', 'enable'] + add_mandatory_fields)
    projects = config.get('projects', {})

    # Ensure there's at least one project.
    if not len(projects):
        raise ConfigException("No project configured.")

    # For all projects, ensure all mandatory fields are present.
    mandatory_keys = set(['path', 'scm', 'enable'] + add_mandatory_fields)
    for project in projects:
        _check_config_section(project, mandatory_keys, prefix='projects')


def check_config(add_mandatory_server_fields=[], add_mandatory_user_fields=[],
                 add_mandatory_project_fields=[]):
    """ Checks all the mandatory fields in all sections.
    """

    check_server(add_mandatory_fields=add_mandatory_server_fields)
    check_user(add_mandatory_fields=add_mandatory_user_fields)
    check_project(add_mandatory_fields=add_mandatory_project_fields)


def dump():
    """ Dumps the config dict to the user's configuration file ~/.baboonrc. If
    the file already exists, it's copied to ~/.baboonrc.old and the original
    file is overwritten.
    """

    # Don't dump the config if the --nosave arg is present.
    if config['parser'].get('nosave', False):
        return

    baboonrc_path = os.path.expanduser('~/.baboonrc')
    baboonrc_old_path = os.path.expanduser('~/.baboonrc.old')

    try:
        # Dump the config file.
        with open(baboonrc_path, 'w') as fd:
            print >>fd, get_dumped_user()
            print >>fd, get_dumped_server()
            print >>fd, get_dumped_projects()
            print >>fd, get_dumped_example_project()

            csuccess("The new configuration file is written in ~/.baboonrc\n")
    except EnvironmentError as err:
        cerr("Cannot dump the configuration. Cause:\n%s" % err)


def get_dumped_server():
    """ Returns a dumped representation of the server section.
    """

    return '\n'.join(_get_dumped_section('server')) + '\n'


def get_dumped_user():
    """ Returns a dumped representation of the user section.
    """

    return '\n'.join(_get_dumped_section('user')) + '\n'


def get_dumped_projects():
    """ Returns a dumped representation of the projects section.
    """

    content = []
    for project, opts in config['projects'].iteritems():
        dumped_section = _get_dumped_section(project, prefix='projects')
        content.append('\n'.join(dumped_section) + '\n')

    return '\n'.join(content)


def get_dumped_example_project():
    """ Returns a dumped representation of project configuration example.
    """

    return """# Example of project definition.
#[awesome_project] \t# The project name on the baboon server.
#path = /pathto/project # The project path of your system.
#scm = git \t\t# The source code manager you use for this project.
#enable = 1 \t\t# You want baboon to actually watch this project.
"""


def get_baboon_config():
    """ Returns the baboon full dict configuration.
    """

    arg_attrs = get_config_args(PARSER)
    file_attrs = get_config_file(arg_attrs, 'baboonrc')
    init_config_log(arg_attrs, LOGGING)

    config = {
        'parser': arg_attrs,
        'projects': {}
    }

    # The known section tuple contains the list of sections to put directly
    # as a root key in the config dict. Other sections will be interpreted as a
    # project and placed into the 'projects' key.
    known_section = ('server', 'user')
    for key in file_attrs:
        if key in known_section:
            config[key] = file_attrs[key]
        else:
            # It's a project, add the attributes to the projects key.
            config['projects'][key] = file_attrs[key]

    # If a hostname has been defined in the command line, we need to override
    # all fields that depend on it.
    depend_hostnames = {}
    if 'server' in config:
        depend_hostnames['server'] = ['pubsub', 'streamer', 'master']
    if 'user' in config:
        depend_hostnames['user'] = ['jid']

    # Search and replace default hostname by hostname defined from the command
    # line.
    for section, fields in depend_hostnames.iteritems():
        for field in fields:
            try:
                cur_value = config[section][field]
                config[section][field] = cur_value.replace(
                    'baboon-project.org', config['parser']['hostname'])
            except KeyError:
                # Just pass the keyerror exception. If it's a mandatory field,
                # the error will be raised correctly later.
                pass

    return config


def _check_config_section(section, mandatory_keys, prefix=None):

    # If the prefix is provided, use the config['prefix'] src dict instead of
    # directly the src config. Useful for projects sections.
    src = config[prefix] if prefix else config

    # Ensure the section exists.
    if section not in src:
        raise ConfigException("'%s' section is missing." % section)

    try:
        # Ensure all mandatory keys exist with a non-empty value. If not,
        # raised a appropriate message exception.
        for key, value in [(x, src[section][x]) for x in mandatory_keys]:
            if not value:
                raise ConfigException("Value of the '%s' field cannot be "
                                      "empty." % key)
    except KeyError as err:
        raise ConfigException("'%s' field required in the '%s' section " %
                              (err.message, section))


def _get_dumped_section(section, prefix=None):

    try:
        src = config[prefix] if prefix else config

        content = ['[%s]' % section]
        for option, value in src['%s' % section].iteritems():
            content.append('%s = %s' % (option, value))

        return content
    except KeyError:
        # Ignore all the section content if a KeyError exception is raised.
        return ''


config = get_baboon_config()
