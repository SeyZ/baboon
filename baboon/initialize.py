import os
import errno
from config import config
from errors.baboon_exception import BaboonException


class Initializor(object):
    def __init__(self):
        metadir = os.path.join(config.path, config.metadir_name)
        try:
            os.mkdir(metadir)
        except OSError, e:
            if e.errno in (errno.EEXIST, errno.ENOENT,):
                raise BaboonException("Baboon error : %s - %s" %
                                      (e.strerror, os.path.abspath(metadir)))
            else:
                raise
