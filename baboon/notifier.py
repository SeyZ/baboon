import os
import pyinotify

from config import config
from diffman import diffman
from service import service


class EventHandler(pyinotify.ProcessEvent):

    def process_IN_CREATE(self, event):
        print "File created : %s" % event.pathname

    def process_IN_MODIFY(self, event):
        filename = os.path.basename(event.pathname)

        old_file_path = "%s%s%s" % (config.metadir_watched, os.sep, filename)
        new_file_path = "%s%s%s" % (config.path, os.sep, filename)

        patch = diffman.diff(old_file_path, new_file_path)
        service.send(patch)


class Notifier(object):
    def __init__(self):
        vm = pyinotify.WatchManager()
        mask = pyinotify.IN_MODIFY | pyinotify.IN_CREATE

        handler = EventHandler()

        notifier = pyinotify.Notifier(vm, handler)
        notifier.coalesce_events()
        vm.add_watch(config.path, mask, rec=True)

        notifier.loop()

    def watch(self):
        self.notifier.loop()
