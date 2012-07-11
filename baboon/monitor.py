import os

from time import sleep
from threading import Thread, Lock
from abc import ABCMeta, abstractmethod, abstractproperty

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import config
from common.logger import logger
from common.errors.baboon_exception import BaboonException

# Stores the list of changed files in the pending set(). The Dancer
# thread will be sync the file when it's necessary. Then this pending
# set() will be cleared.
pending = set()
del_pending = set()
mov_pending = set()

# A thread lock object in order to access to the pending object thread
# safety.
lock = Lock()


@logger
class EventHandler(FileSystemEventHandler):
    """ An abstract class that extends watchdog FileSystemEventHandler in
    order to describe the behavior when a file is
    added/modified/deleted. The behavior is dependend of the SCM to
    detect exclude patterns (e.g. .git for git, .hg for hg, etc.)
    """

    __metaclass__ = ABCMeta

    def __init__(self, transport):
        """ Take the transport to rsync the changes on baboon server.
        """

        super(EventHandler, self).__init__()
        self.transport = transport

    @abstractproperty
    def scm_name(self):
        """ The name of the scm. This name will be used in the baboonrc
        configuration file in order to retrieve and instanciate the correct
        class.
        """

        return

    @abstractmethod
    def exclude(self, path):
        '''Returns True when file matches an exclude pattern specified in the
        scm specific monitor plugin.
        '''
        return

    def on_moved(self, event):
        rel_path = self._verify_exclude(event, event.dest_path)
        if rel_path:
            # Acquire the thread lock and add the rel_path of the
            # changed file in the pending set().
            with lock:
                # Add the src path to the del_pending set() to remove
                # the file remotely.
                src_rel_path = os.path.relpath(event.src_path, config.path)
                del_pending.add(src_rel_path)

                # Add the dest path to the pending set() to add the
                # file remotely.
                pending.add(rel_path)

    def on_created(self, event):
        self.on_modified(event)

    def on_modified(self, event):
        """ Triggered when a file is modified in the watched project.
        @param event: the watchdog event
        @raise BaboonException: if cannot retrieve the relative project path
        """

        rel_path = self._verify_exclude(event, event.src_path)
        if rel_path:
            # Here, we are sure that the rel_path is a file. The check
            # is done if the _verify_exclude method.

            # If the file was a file and is now a directory, we need
            # to delete absolutely the file. Otherwise, the server
            # will not create the directory (OSError).
            if os.path.isdir(event.src_path):
                self.logger.info('The file %s is now a directory.' % rel_path)
                # Acquire the thread lock and add the file to the
                # del_pending set().
                with lock:
                    del_pending.add(rel_path)
            else:
                # Acquire the thread lock and add the rel_path of the
                # changed file in the pending set().
                with lock:
                    pending.add(rel_path)

    def on_deleted(self, event):
        """ Trigered when a file is deleted in the watched project.
        """

        # Check if the event path does not exist anymore. For example,
        # when you do a 'git checkout .' in the watched directory, the
        # on_deleted watchdog event is triggered but the file is not
        # really deleted. In this case, redirect the event to the
        # on_modified handler.
        if not os.path.exists(event.src_path):
            rel_path = self._verify_exclude(event, event.src_path)
            if rel_path:
                # Acquire the thread lock and add the rel_path of the
                # changed file in the pending_del_files set().
                with lock:
                    del_pending.add(rel_path)
        else:
            self.on_modified(event)

    def _verify_exclude(self, event, fullpath):
        """ Verifies if the full path correspond to an exclude
        file. Returns the relative path of the file if the file is not
        excluded. Returns None if the file need to be ignored.
        """

        # Use the event is_directory attribute instead of
        # os.path.isdir. Suppose a file 'foo' is deleted and a
        # directory named 'foo' is created. The on_deleted is
        # triggered after the file is deleted and maybe after the
        # directory is created too. So if we do a os.path.isdir, the
        # return value will be True. We want False.
        if event.is_directory:
            return None

        rel_path = os.path.relpath(fullpath, config.path)
        if self.exclude(rel_path):
            self.logger.debug("Ignore the file: %s" % rel_path)
            return

        return rel_path


class Dancer(Thread):
    """ A thread that wakes up every <sleeptime> secs and starts a
    rsync + merge verification if pending set() is not empty.
    """

    def __init__(self, transport, sleeptime=1):
        """ Initializes the thread.
        """

        Thread.__init__(self)

        self.transport = transport
        self.sleeptime = sleeptime
        self.stop = False

    def run(self):
        """ Runs the thread.
        """
        global pending, mov_pending, del_pending

        while not self.stop:
            # Sleeps during sleeptime secs.
            sleep(self.sleeptime)

            # Acquires the lock in order to manipulate the pending
            # changed file in the pending set().
            with lock:
                # If there's at least 1 element in the pending or
                # del_pending  or mov_pending set()...
                if pending or del_pending or mov_pending:
                    try:
                        # Avoid to sync a file that needs to be delete
                        # after.
                        pending -= del_pending

                        # Starts the rsync.
                        self.transport.rsync(files=pending,
                                             mov_files=mov_pending,
                                             del_files=del_pending)

                        # Clears the pending set().
                        pending.clear()
                        mov_pending.clear()
                        del_pending.clear()

                        # Asks to baboon to verify if there's a conflict
                        # or not.
                        self.transport.merge_verification()

                    except BaboonException, e:
                        self.logger.error(e)

    def close(self):
        """ Sets the stop flag to True.
        """

        self.stop = True


@logger
class Monitor(object):
    def __init__(self, transport):
        """ Watches file change events (creation, modification) in the
        watched project.
        """

        self.transport = transport

        # Initialize the event handler class to use depending on the SCM to use
        handler = None
        scm_classes = EventHandler.__subclasses__()

        for cls in scm_classes:
            tmp_inst = cls(self.transport)
            if tmp_inst.scm_name == config.scm:
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

        self.monitor = Observer()
        self.dancer = Dancer(self.transport, sleeptime=1)
        try:
            self.monitor.schedule(handler, config.path, recursive=True)
        except OSError, err:
            self.logger.error(err)
            raise BaboonException(err)

    def watch(self):
        """ Starts to watch the watched project
        """

        self.monitor.start()
        self.dancer.start()
        self.logger.debug("Started to monitor the %s directory"
                         % config.path)

    def close(self):
        """ Stops the monitoring on the watched project
        """

        self.monitor.stop()
        self.monitor.join()

        self.dancer.close()
        self.dancer.join()
