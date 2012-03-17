from abc import ABCMeta, abstractmethod, abstractproperty
from config import Config


class Diffman(object):
    __metaclass__ = ABCMeta

    @abstractproperty
    def scm_name(self):
        return

    def __init__(self):
        self.config = Config()

    @abstractmethod
    def diff(self, filepath):
        """ Computes the diff of the filepath
        """
        return

    @abstractmethod
    def patch(self, patch, thefile, content=None):
        """
        """

    def _escape(self, text):
        escaped_text = map(lambda x: "<![CDATA[%s]]>" % x, text.split("]]>"))
        return "<![CDATA[]]]><![CDATA[]>]]>".join(escaped_text)
