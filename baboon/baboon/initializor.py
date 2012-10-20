import os
import shutil
import time
import shelve

from os.path import join, relpath, getmtime, exists

from baboon.baboon.config import config
from baboon.common.file import FileEvent
from baboon.common.eventbus import eventbus
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


@logger
class MetadirController(object):

    METADIR = '.baboon'
    GIT_INDEX = 'index'

    def __init__(self, project, project_path, exclude_method=None):
        """
        """

        self.project = project
        self.project_path = project_path
        self.metadir_path = join(self.project_path, MetadirController.METADIR)
        self.exclude_method = exclude_method

        eventbus.register('rsync-finished-success', self._on_rsync_finished)

    def go(self):
        """
        """

        # Verify (and create if necessary) if baboon metadir exists.
        already_exists = exists(self.metadir_path)

        if already_exists:
            # Initializes the shelve index.
            self.init_index()

            # Startup initialization.
            self._startup_init()
        else:
            raise BaboonException("The project %s is not yet initialized. "
                                  "Please, run `baboon init %s <git-url>`." %
                                  (self.project, self.project))

    def init_index(self):
        if not exists(self.metadir_path):
            os.makedirs(self.metadir_path)

        self.index = shelve.open(join(self.metadir_path,
                                      MetadirController.GIT_INDEX),
                                 writeback=True)

    def create_baboon_index(self):
        """
        """

        if not exists(self.metadir_path):
            os.makedirs(self.metadir_path)

        cur_timestamp = time.time()

        for root, _, files in os.walk(self.project_path):
            for name in files:
                fullpath = join(root, name)
                rel_path = relpath(fullpath, self.project_path)

                self.index[rel_path] = cur_timestamp

    def _on_rsync_finished(self, project, files):
        """ When a rsync is finished, update the index dict.
        """

        # First, we need to verify if the event is for this current
        # initializor! If so, it means the project is the same than
        # self.project.
        if not project == self.project:
            return

        cur_timestamp = time.time()

        try:
            for f in files:
                if f.event_type == FileEvent.MOVE:
                    del self.index[f.src_path]
                    self.index[f.dest_path] = cur_timestamp
                elif f.event_type == FileEvent.DELETE:
                    del self.index[f.src_path]
                else:
                    self.index[f.src_path] = cur_timestamp

            # TODO: Verify if it's not a performance issue (maybe on big
            # project).
            self.index.sync()
        except ValueError:
            # If the index shelve is already closed, a ValueError is raised.
            # In this case, the last rsync will not be persisted on disk. Not
            # dramatical.
            pass

    def _startup_init(self):
        """
        """

        cur_files = []

        self.logger.info("[%s] startup initialization..." % self.project)
        for root, _, files in os.walk(self.project_path):
            for name in files:
                fullpath = join(root, name)
                rel_path = relpath(fullpath, self.project_path)

                # Add the current file to the cur_files list.
                cur_files.append(rel_path)

                # Get the last modification timestamp of the current file.
                cur_timestamp = getmtime(fullpath)

                # Get the last rsync timestamp of the current file.
                register_timestamp = self.index.get(rel_path)

                # If the file is not excluded...
                if not self.exclude_method or not \
                        self.exclude_method(rel_path):
                    # Verify if it's a new file...
                    if register_timestamp is None:
                        self.logger.info("Need to create: %s" % rel_path)
                        FileEvent(self.project, FileEvent.CREATE,
                                  rel_path).register()
                    elif (register_timestamp and cur_timestamp >
                          register_timestamp):
                        self.logger.info("Need to sync: %s" % rel_path)
                        FileEvent(self.project, FileEvent.MODIF,
                                  rel_path).register()

        # Verify if there's no file deleted since the last time.
        for del_file in [x for x in self.index.keys() if x not in cur_files]:
            self.logger.info("Need to delete: %s" % del_file)
            FileEvent(self.project, FileEvent.DELETE, del_file).register()

        self.logger.info("[%s] ready !" % self.project)

    def delete(self):
        """ Deletes the metadir from the project.
        """

        if os.path.exists(self.metadir_path):
            shutil.rmtree(self.metadir_path)
