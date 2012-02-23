import os
import pyinotify

from config import config


class EventHandler(pyinotify.ProcessEvent):

    def __init__(self, service):
        super(EventHandler, self).__init__()
        self.service = service

    def process_IN_CREATE(self, event):
        print "File created : %s" % event.pathname

    def process_IN_MODIFY(self, event):
        print "File modified : %s" % event.pathname

        filename = os.path.basename(event.pathname)

        old_file_path = "%s%s%s" % (config.metadir_watched, os.sep, filename)
        new_file_path = "%s%s%s" % (config.path, os.sep, filename)

        patch = self.service.make_patch(old_file_path, new_file_path)
        self.service.broadcast(patch)


class Monitor(object):
    def __init__(self, service):
        self.service = service

        vm = pyinotify.WatchManager()
        mask = pyinotify.IN_MODIFY | pyinotify.IN_CREATE

        handler = EventHandler(service)

        self.monitor = pyinotify.ThreadedNotifier(vm, handler)
        self.monitor.coalesce_events()
        vm.add_watch(config.path, mask, rec=True)

    def watch(self):
        self.monitor.start()
