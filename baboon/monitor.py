import re
import pyinotify

from abc import ABCMeta, abstractmethod, abstractproperty
from errors.baboon_exception import BaboonException
from logger import logger
from config import Config


class EventHandler(pyinotify.ProcessEvent):
    __metaclass__ = ABCMeta

    def __init__(self, service):
        """ @param service: the service in order to call some baboon util
        methods.
        """
        super(EventHandler, self).__init__()
        self.config = Config()
        self.service = service

    @abstractproperty
    def scm_name(self):
        """ The name of the scm. This name will be used in the baboonrc
        configuration file in order to retrieve and instanciate the correct
        class.
        """
        return

    @abstractmethod
    def exclude_paths(self):
        """ A list of regexp patterns to exclude from the Watcher
        """
        return

    def process_IN_CREATE(self, event):
        """ Triggered when a file is created in the watched project.
        @param event: the event provided by pyinotify.ProcessEvent.
        """
        pass

    def process_IN_MODIFY(self, event):
        """ Triggered when a file is modified in the watched project.
        @param event: the event provided by pyinotify.ProcessEvent.
        @raise BaboonException: if cannot retrieve the relative project path
        """
        fullpath = event.pathname
        rel_path = self.get_rel_path(fullpath)

        for excl in self.exclude_paths():
            if re.search(excl, fullpath):
                return

        self.service.broadcast(rel_path)

    def process_IN_DELETE(self, event):
        """ Trigered when a file is deleted in the watched project.
        """
        self.process_IN_MODIFY(event)

    def get_rel_path(self, fullpath):
        rel_path = None
        try:
            rel_path = fullpath.split(self.config.path)[1]
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]
        except:
            err = 'Cannot retrieve the relative project path'
            raise BaboonException(err)

        return rel_path


@logger
class Monitor(object):
    def __init__(self, service):
        """ Watches file change events (creation, modification) in the
        watched project.
        @param service: Forwards the service to the L{EventHandler} class
        """
        self.config = Config()
        self.service = service

        vm = pyinotify.WatchManager()
        mask = pyinotify.IN_CREATE | pyinotify.IN_MODIFY | pyinotify.IN_DELETE

        # Initialize the event handler class to use depending on the SCM to use
        handler = None
        scm_classes = EventHandler.__subclasses__()
        for cls in scm_classes:
            tmp_inst = cls(service)
            if tmp_inst.scm_name == self.config.scm:
                handler = tmp_inst

        if handler is None:
            raise BaboonException("Cannot get a valid FS event handler class"
                                  " for your SCM written in your baboonrc"
                                  " file")

        self.monitor = pyinotify.ThreadedNotifier(vm, handler)
        self.monitor.coalesce_events()

        # get the exclude path from the current SCM plugin
        exclude_paths = pyinotify.ExcludeFilter(handler.exclude_paths())

        # add the watcher
        vm.add_watch(self.config.path, mask, rec=True,
                     exclude_filter=exclude_paths)

    def watch(self):
        """ Starts to watch the watched project
        """
        self.monitor.start()
        self.logger.info("Started to monitor the %s directory"
                         % self.config.path)

    def close(self):
        """ Stops the monitoring on the watched project
        """
        self.monitor.stop()
