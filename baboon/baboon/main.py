import os
import sys
import logging

from baboon.common.errors.baboon_exception import ConfigException

# The config can raise a ConfigException if there's a problem.
try:
    from baboon.baboon.config import config
    from baboon.baboon.config import check_server, check_user, check_project
except ConfigException as err:
    # An error as occured while loading the global baboon configuration. So,
    # there's no logger correctly configured. Load a basic logger to print the
    # error message.

    logging.basicConfig(format='%(message)s')
    logger = logging.getLogger(__name__)
    logger.error(err)

    sys.exit(1)

from baboon.baboon import commands
from baboon.baboon.plugins import *
from baboon.common.logger import logger

logger = logging.getLogger(__name__)


def main():
    """ The entry point of the Baboon client.
    """

    try:
        # Call the correct method according to the current arg subparser.
        getattr(commands, config['parser']['which'])()
    except (ConfigException, KeyError) as err:
        logger.error(err)
        sys.exit(1)
