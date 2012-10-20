import os
import tarfile
import tempfile

from os.path import join, exists
from time import sleep
from threading import Thread, Lock
from abc import ABCMeta, abstractmethod, abstractproperty

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from baboon.baboon.config import config
from baboon.common.file import FileEvent, pending
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException

lock = Lock()


@logger
class EventHandler(FileSystemEventHandler):
    """ An abstract class that extends watchdog FileSystemEventHandler in
    order to describe the behavior when a file is
    added/modified/deleted. The behavior is dependend of the SCM to
    detect exclude patterns (e.g. .git for git, .hg for hg, etc.)
    """

    __metaclass__ = ABCMeta

    def __init__(self, project_path):

        super(EventHandler, self).__init__()
        self.project_path = project_path

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

    def on_created(self, event):
        self.logger.debug('CREATED event %s' % event.src_path)

        with lock:
            project = self._get_project(event.src_path)
            rel_path = self._verify_exclude(event, event.src_path)
            if rel_path:
                FileEvent(project, FileEvent.CREATE, rel_path).register()

    def on_moved(self, event):
        self.logger.debug('MOVED event from %s to %s' % (event.src_path,
                                                         event.dest_path))

        with lock:
            project = self._get_project(event.src_path)
            src_rel_path = self._verify_exclude(event, event.src_path)
            dest_rel_path = self._verify_exclude(event, event.dest_path)

            if src_rel_path:
                FileEvent(project, FileEvent.DELETE, src_rel_path).register()

            if dest_rel_path:
                FileEvent(project, FileEvent.MODIF, dest_rel_path).register()

    def on_modified(self, event):
        """ Triggered when a file is modified in the watched project.
        @param event: the watchdog event
        @raise BaboonException: if cannot retrieve the relative project path
        """

        self.logger.debug('MODIFIED event %s' % event.src_path)

        with lock:
            project = self._get_project(event.src_path)
            rel_path = self._verify_exclude(event, event.src_path)
            if rel_path:
                # Here, we are sure that the rel_path is a file. The check is
                # done if the _verify_exclude method.

                # If the file was a file and is now a directory, we need to
                # delete absolutely the file. Otherwise, the server will not
                # create the directory (OSError).
                if os.path.isdir(event.src_path):
                    self.logger.debug('The file %s is now a directory.' %
                                      rel_path)

                FileEvent(project, FileEvent.MODIF, rel_path).register()

    def on_deleted(self, event):
        """ Trigered when a file is deleted in the watched project.
        """

        self.logger.debug('DELETED event %s' % event.src_path)

        with lock:
            project = self._get_project(event.src_path)
            rel_path = self._verify_exclude(event, event.src_path)
            if rel_path:
                FileEvent(project, FileEvent.DELETE, rel_path).register()

    def _verify_exclude(self, event, fullpath):
        """ Verifies if the full path correspond to an exclude file. Returns
        the relative path of the file if the file is not excluded. Returns None
        if the file need to be ignored.  """

        # Use the event is_directory attribute instead of
        # os.path.isdir. Suppose a file 'foo' is deleted and a
        # directory named 'foo' is created. The on_deleted is
        # triggered after the file is deleted and maybe after the
        # directory is created too. So if we do a os.path.isdir, the
        # return value will be True. We want False.
        if event.is_directory:
            return None

        rel_path = os.path.relpath(fullpath, self.project_path)
        if self.exclude(rel_path):
            self.logger.debug("Ignore the file: %s" % rel_path)
            return

        return rel_path

    def _get_project(self, fullpath):
        """ Get the name of the project of the fullpath file.
        """

        for project, project_conf in config['projects'].iteritems():
            path = os.path.expanduser(project_conf['path'])
            if path == self.project_path:
                return project


@logger
class Dancer(Thread):
    """ A thread that wakes up every <sleeptime> secs and starts a
    rsync + merge verification if pending set() is not empty.
    """

    def __init__(self, sleeptime=1):
        """ Initializes the thread.
        """

        Thread.__init__(self, name='Dancer')

        self.sleeptime = sleeptime
        self.stop = False

    def run(self):
        """ Runs the thread.
        """

        while not self.stop:
            # Sleeps during sleeptime secs.
            sleep(self.sleeptime)

            with lock:
                for project, files in pending.iteritems():
                    try:
                        eventbus.fire('new-rsync', project=project,
                                      files=files)

                    except BaboonException as e:
                        self.logger.error(e)

                # Clears the pending dict.
                pending.clear()

    def close(self):
        """ Sets the stop flag to True.
        """

        self.stop = True


@logger
class Monitor(object):
    def __init__(self):
        """ Watches file change events (creation, modification) in the
        watched project.
        """

        from baboon.baboon.plugins.git.monitor_git import EventHandlerGit

        self.dancer = Dancer(sleeptime=1)

        # All monitor will be stored in this dict. The key is the project name,
        # the value is the monitor instance.
        self.monitors = {}

        try:
            # Avoid to use iteritems (python 2.x) or items (python 3.x) in
            # order to support both versions.
            for project in sorted(config['projects']):
                project_attrs = config['projects'][project]
                project_path = os.path.expanduser(project_attrs['path'])
                self.handler = EventHandlerGit(project_path)

                monitor = Observer()
                monitor.schedule(self.handler, project_path, recursive=True)

                self.monitors[project_path] = monitor
        except OSError as err:
            self.logger.error(err)
            raise BaboonException(err)

    def watch(self):
        """ Starts to watch the watched project
        """

        # Start all monitor instance.
        for project, monitor in self.monitors.iteritems():
            monitor.start()
            self.logger.debug("Started to monitor the %s directory" % project)

        self.dancer.start()

    def startup_rsync(self, project, project_path):
        """
        """

        # Get the timestamp of the last rsync.
        register_timestamp = os.path.getmtime(join(project_path,
                                                   '.baboon-timestamp'))

        for root, _, files in os.walk(project_path):
            for name in files:
                fullpath = join(root, name)
                rel_path = os.path.relpath(fullpath, project_path)

                # Get the timestamp of the current file
                cur_timestamp = os.path.getmtime(fullpath)

                # Register a FileEvent.MODIF if the file is not excluded
                # and the file is more recent than the last rsync.
                if not self.handler.exclude(rel_path) and \
                        cur_timestamp > register_timestamp:

                    FileEvent(project, FileEvent.MODIF, rel_path).register()

    def close(self):
        """ Stops the monitoring on the watched project
        """

        # Stop all monitor instance.
        for project, monitor in self.monitors.iteritems():
            monitor.stop()
            monitor.join()

        self.dancer.close()
        self.dancer.join()
