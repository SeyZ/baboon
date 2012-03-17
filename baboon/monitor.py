import os
import pyinotify
import shutil

from fnmatch import fnmatch
from errors.baboon_exception import BaboonException
from logger import logger
from config import Config


@logger
class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, service):
        """ @param service: the service in order to call some baboon util
        methods.
        """
        super(EventHandler, self).__init__()
        self.config = Config()
        self.service = service

    def process_IN_CREATE(self, event):
        """ Triggered when a file is created in the watched project.
        @param event: the event provided by pyinotify.ProcessEvent.
        """
        self.logger.info("File created : %s" % event.pathname)

    def process_IN_MODIFY(self, event):
        """ Triggered when a file is modified in the watched project.
        @param event: the event provided by pyinotify.ProcessEvent.
        @raise BaboonException: if cannot retrieve the relative project path
        """
        # verifies the filename doesn't match an ignore patterns
        fullpath = event.pathname
        rel_path = None
        try:
            rel_path = fullpath.split(self.config.path)[1]
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]
        except:
            err = 'Cannot retrieve the relative project path'
            raise BaboonException(err)

        for pattern in self.config.ignore_patterns:
            if fnmatch(rel_path, pattern):
                self.logger.debug("Ignored the modify event on %s (match "
                                  "the ignore pattern %s)."
                                  % (fullpath, pattern))
                # ignore IN_MODIFY event if matched
                return

        self.logger.info("Received %s event type of file %s" %
                         (event.maskname, event.pathname))

        old_file_path = "%s%s%s" % (self.config.metadir_watched, os.sep,
                                    rel_path)
        new_file_path = "%s%s%s" % (self.config.path, os.sep, rel_path)

        patch = self.service.make_patch(old_file_path, new_file_path)

        self.service.broadcast(rel_path, patch)

    def process_IN_DELETE(self, event):
        """ Trigered when a file is deleted in the watched project.
        """
        self.process_IN_MODIFY(event)


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
        mask = pyinotify.IN_MODIFY | pyinotify.IN_CREATE | pyinotify.IN_DELETE

        handler = EventHandler(service)

        self.monitor = pyinotify.ThreadedNotifier(vm, handler)
        self.monitor.coalesce_events()
        vm.add_watch(self.config.path, mask, rec=True)

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
