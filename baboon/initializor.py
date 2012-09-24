import os
import shutil
import time
import shelve

from os.path import join, relpath, getmtime, exists

from config import config
from common.file import FileEvent
from common.eventbus import eventbus
from common.logger import logger
from common.errors.baboon_exception import BaboonException


@logger
class MetadirController(object):

    METADIR = '.baboon'
    GIT_INDEX = 'index'

    def __init__(self, transport, project, project_path, exclude_method=None):
        """
        """

        self.transport = transport
        self.project = project
        self.project_path = project_path
        self.exclude_method = exclude_method

        eventbus.register('rsync-finished-success', self._on_rsync_finished)

    def go(self):
        """
        """

        already_exists = self._create_missing_metadir()
        self.index = shelve.open(join(self.project_path,
                                      MetadirController.METADIR,
                                      MetadirController.GIT_INDEX),
                                 writeback=True)
        if not already_exists:
            # First repository initialization needed.
            self._first_init()
            self._create_baboon_index()
        else:
            # Startup rsync needed.
            self._startup_init()

    def _on_rsync_finished(self, project, files):
        """ When a rsync is finished, update the index dict.
        """

        # First, we need to verify if the event is for this current
        # initializor! If so, it means the project is the same than
        # self.project.
        if not project == self.project:
            return

        cur_timestamp = time.time()

        for f in files:
            if f.event_type == FileEvent.MOVE:
                del self.index[f.src_path]
                self.index[f.dest_path] = cur_timestamp
            elif f.event_type == FileEvent.DELETE:
                del self.index[f.src_path]
            else:
                self.index[f.src_path] = cur_timestamp

        # TODO: Verify if it's not a performance issue (maybe on big project).
        self.index.sync()

    def _create_missing_metadir(self):
        """ Create the baboon metadir if it does not exist in the project path.
        If the metadir already exists, return True. Otherwise, False.
        """

        metadir_path = join(self.project_path, MetadirController.METADIR)

        if exists(metadir_path):
            return True
        else:
            os.makedirs(metadir_path)
            return False

    def _create_baboon_index(self):
        """
        """

        cur_timestamp = time.time()

        for root, _, files in os.walk(self.project_path):
            for name in files:
                fullpath = join(root, name)
                rel_path = relpath(fullpath, self.project_path)

                self.index[rel_path] = cur_timestamp

    def _first_init(self):
        """
        """

        git_url = config['parser']['git-url']
        if git_url:
            self.transport.first_git_init(self.project, git_url)
        else:
            shutil.rmtree(join(self.project_path, MetadirController.METADIR))
            raise BaboonException("The project is not yet "
                                  "initialized. Please, add the "
                                  "--git-url option with the url "
                                  "of your public git repository.")

    def _startup_init(self):
        """
        """

        cur_files = []

        self.logger.info("Startup...")
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
                if (not self.exclude_method or not
                    self.exclude_method(rel_path)):

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

        self.logger.info("Ok, ready !")

