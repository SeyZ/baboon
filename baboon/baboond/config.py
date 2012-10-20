import argparse
import logging
import logging.config

from baboon.common.config import get_config_args, get_config_file
from baboon.common.config import init_config_log
from dictconf import LOGGING, PARSER


def get_baboond_config():
    """ Returns the baboond full dict configuration.
    """

    arg_attrs = get_config_args(PARSER)
    file_attrs = get_config_file(arg_attrs, 'baboondrc')
    init_config_log(arg_attrs, LOGGING)

    config = {}
    config.update(arg_attrs)
    config.update(file_attrs)

    return config


config = get_baboond_config()
