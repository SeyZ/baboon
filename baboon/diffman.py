from abc import ABCMeta, abstractmethod, abstractproperty
from config import Config


class Diffman(object):
    __metaclass__ = ABCMeta

    @abstractproperty
    def scm_name(self):
        """ The name of the scm. This name will be used in the baboonrc
        configuration file in order to retrieve and instanciate the correct
        class.
        """
        return

    def __init__(self):
        self.config = Config()

    @abstractmethod
    def diff(self, filepath):
        """ Computes the diff between HEAD and the current working state of
        the filepath
        """
        return

    @abstractmethod
    def patch(self, patch, thefile, content=None):
        """ Checks if the file can be patched with the patch.
        Return True if there's no conflict.
        """
