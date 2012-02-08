import pyinotify

from config import config


class EventHandler(pyinotify.ProcessEvent):
   def process_IN_CREATE(self, event):
      print "File created : %s" % event.pathname

   def process_IN_MODIFY(self, event):
      print "File modified : %s" % event.pathname
      with open(event.pathname) as f:
         content = f.readlines()
         print content


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
