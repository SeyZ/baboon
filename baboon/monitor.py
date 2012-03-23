import os
import re
import pyinotify

from abc import ABCMeta, abstractmethod, abstractproperty
from errors.baboon_exception import BaboonException
from logger import logger
from config import Config


@logger
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
        rel_path = os.path.relpath(fullpath, self.config.path)
        excls = self.exclude_paths()

        for excl in excls[1]:
            regexp = re.compile(excl)
            # If the rel_path matches the current exclude regexp, we
            # need to test if the rel_path matches at least one
            # include regexp.
            if regexp.search(rel_path) is not None:
                self.logger.debug("The path %s matches the ignore regexp"
                                  " %s." % (rel_path, excl))
                # If no, avoids to broadcast the diff
                if not self._match_incl_regexp(excls, rel_path):
                    break
        else:
            # Broadcasts the change on the rel_path if there's no
            # break above.
            self.service.broadcast(rel_path)
            return

        # Here only if the broadcast has not been done.
        self.logger.debug("Ignore the modification on %s" %
                          rel_path)

    def process_IN_DELETE(self, event):
        """ Trigered when a file is deleted in the watched project.
        """
        self.process_IN_MODIFY(event)

    def _match_incl_regexp(self, excls, rel_path):
        for incl in excls[0]:
            neg_regexp = re.compile(incl)
            # si ca match
            if neg_regexp.search(rel_path) is not None:
                self.logger.debug("The same path %s matches the include"
                                  " regexp %s." % (rel_path, incl))
                return True

        return False


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
                self.logger.debug("Uses the %s class for the monitoring of FS "
                                  "changes" % tmp_inst.scm_name)
                handler = tmp_inst
                break
            else:
                # Raises this BaboonException if no plugin has found
                # according to the scm entry in the config file
                raise BaboonException("Cannot get a valid FS event handler"
                                      " class for your SCM written in your"
                                      " baboonrc file")

        self.monitor = pyinotify.ThreadedNotifier(vm, handler)
        self.monitor.coalesce_events()

        # add the watcher
        vm.add_watch(self.config.path, mask, rec=True, auto_add=True)

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
