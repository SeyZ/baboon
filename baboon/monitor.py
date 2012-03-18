import os
import pyinotify

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
        if self._is_hidden(event.pathname):
            return
        self.logger.info("File created : %s" % event.pathname)

    def process_IN_MODIFY(self, event):
        """ Triggered when a file is modified in the watched project.
        @param event: the event provided by pyinotify.ProcessEvent.
        @raise BaboonException: if cannot retrieve the relative project path
        """
        fullpath = event.pathname

        if self._is_hidden(fullpath):
            return

        rel_path = None
        try:
            rel_path = fullpath.split(self.config.path)[1]
            if rel_path.startswith('/'):
                rel_path = rel_path[1:]
        except:
            err = 'Cannot retrieve the relative project path'
            raise BaboonException(err)

        # TODO: Depend on mercurial, ugly thing ! Cannot be here !
        if rel_path.startswith('hg-check'):
            return

        self.logger.info("Received %s event type of file %s" %
                         (event.maskname, fullpath))
        self.service.broadcast(rel_path)

    def process_IN_DELETE(self, event):
        """ Trigered when a file is deleted in the watched project.
        """
        self.process_IN_MODIFY(event)

    def _is_hidden(self, filepath):
        name = os.path.basename(os.path.abspath(filepath))
        return name.startswith('.')


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
