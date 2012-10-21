import os
import errno
import stat
import subprocess
import threading
import shutil
import tempfile
import uuid
import re

from sleekxmpp.jid import JID

from baboon.baboond.dispatcher import dispatcher
from baboon.baboond.transport import transport
from baboon.baboond.config import config
from baboon.common import pyrsync
from baboon.common.eventbus import eventbus
from baboon.common.file import FileEvent
from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


def create_missing_dirs(fullpath, isfile=True):
    """ Creates all missing parent directories of the fullpath.
    """

    if isfile:
        fullpath = os.path.dirname(fullpath)

    try:
        # Creates all the parent directories.
        os.makedirs(fullpath)
    except OSError:
        pass


def exec_cmd(cmd, cwd):
    """ Execute the cmd command in a subprocess.
    """

    # Create the process and run it.
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, shell=True, cwd=cwd)
    output, errors = proc.communicate()

    return (proc.returncode, output, errors)


class Task(object):
    """ The base class for all kind of tasks.
    """

    def __init__(self, priority):
        """ Store the priority in order to compare tasks and order
        them.
        """
        self.priority = priority

    def __cmp__(self, other):
        """ The comparison is based on the priority.
        """
        return cmp(self.priority, other.priority)

    def run(self):
        """ This task cannot be run.
        """
        raise NotImplementedError("This run method must be implemented in a "
                                  " task subclass.")


@logger
class EndTask(Task):
    """ A high priority task to exit BaboonSrv.
    """

    def __init__(self):
        """ Initializes the EndTask.
        """

        # The priority is 1. It means that it's the higher possible priority
        # for baboonsrv.
        super(EndTask, self).__init__(1)

    def run(self):
        """ Shutdowns Baboond.
        """

        # Closes the transport
        transport.close()
        self.logger.info('Bye !')


class AlertTask(Task):
    """ A high priority task to alert baboon client the state of the merge.
    """

    def __init__(self, project_name, username, dest_username,
                 merge_conflict=False, conflict_files=[]):
        """ Initialize the AlertTask. By default, there's no merge
        conflict.
        """

        # The priority is 2. It means that it's the higher possible
        # priority for baboonsrv except the EndTask.
        super(AlertTask, self).__init__(2)

        self.project_name = project_name
        self.username = username
        self.dest_username = dest_username
        self.merge_conflict = merge_conflict
        self.conflict_files = conflict_files

    def run(self):
        """ Build the appropriate message and publish it to the node.
        """

        conflict_msg = 'Conflict detected with %s and %s.' % (
            self.username, self.dest_username)
        good_msg = 'Everything seems to be perfect.'
        msg = conflict_msg if self.merge_conflict else good_msg

        transport.alert(self.project_name, msg, self.conflict_files)


@logger
class GitInitTask(Task):
    """ The first git initialization task. In other words, the first git clone.
    """

    def __init__(self, project, url, jid):
        """ Initializes the GitInitTask.
        """

        super(GitInitTask, self).__init__(4)

        # Generate the current GitInitTask unique baboon id
        self.bid = uuid.uuid4()

        self.project = project
        self.url = url
        self.jid = jid
        self.project_cwd = os.path.join(config['server']['working_dir'],
                                        self.project)
        self.user_cwd = os.path.join(self.project_cwd, self.jid)

    def run(self):
        self.logger.debug('A new git init task has been started.')

        # If the project directory already exists, delete it.
        if os.path.exists(self.user_cwd):
            shutil.rmtree(self.user_cwd)

        create_missing_dirs(self.project_cwd, isfile=False)
        ret_code, output, _ = exec_cmd('git clone %s %s' % (
            self.url, self.jid), self.project_cwd)
        if not ret_code:
            self.logger.debug('Git init task finished.')
            eventbus.fire('git-init-success', self.bid)
        else:
            eventbus.fire('git-init-failure', self.bid,
                          "Cannot initialize the git repository.")


@logger
class RsyncTask(Task):
    """ A rsync task to sync the baboon client repository with
    relative repository server-side.
    """

    def __init__(self, sid, rid, sfrom, project, project_path, files):

        super(RsyncTask, self).__init__(4)

        self.sid = sid
        self.rid = rid
        self.jid = JID(sfrom)
        self.project = project
        self.project_path = project_path
        self.files = files

        self.modif_files = []
        self.create_files = []
        self.mov_files = []
        self.del_files = []

        # Declare a thread Event to wait until the rsync is completely
        # finished.
        self.rsync_finished = threading.Event()

    def run(self):

        self.logger.debug('RsyncTask %s started' % self.sid)

        # Lock the repository with a .baboon.lock file.
        lock_file = os.path.join(self.project_path, '.baboon.lock')
        create_missing_dirs(lock_file)
        open(lock_file, 'w').close()

        for f in self.files:
            # Verify if the file can be written in the self.project_path.
            path_valid = self._verify_paths(f)
            if not path_valid:
                self.logger.error("The file path cannot be written in %s." %
                                  self.project)
                eventbus.fire('rsync-finished-failure', rid=self.rid)
                return

            if f.event_type == FileEvent.CREATE:
                self.logger.debug('[%s] - Need to create %s.' %
                                 (self.project_path, f.src_path))
                self._create_file(f.src_path)
            elif f.event_type == FileEvent.MODIF:
                self.logger.debug('[%s] - Need to sync %s.' %
                                 (self.project_path, f.src_path))
                new_hash = self._get_hash(f.src_path)
                self._send_hash(new_hash)
            elif f.event_type == FileEvent.DELETE:
                self.logger.debug('[%s] - Need to delete %s.' %
                                 (self.project_path, f.src_path))
                self._delete_file(f.src_path)
            elif f.event_type == FileEvent.MOVE:
                self.logger.debug('[%s] - Need to move %s to %s.' %
                                 (self.project_path, f.src_path, f.dest_path))
                self._move_file(f.src_path, f.dest_path)

        # Remove the .baboon.lock file.
        os.remove(lock_file)

        # Fire the rsync-finished-success event.
        eventbus.fire('rsync-finished-success', rid=self.rid)

        self.logger.debug('Rsync task %s finished', self.sid)

    def _verify_paths(self, file_event):
        """ Verifies if the file_event paths can be written in the
        project_path.
        """

        valid = self._verify_path(file_event.src_path)
        if valid and file_event.dest_path:
            valid = self._verify_path(file_event.dest_path)

        return valid

    def _verify_path(self, f):
        """ Verifies if the f path can be written in the project_path.
        """

        joined = os.path.join(self.project_path, f)
        if self.project_path not in os.path.abspath(joined):
            return False

        return True

    def _create_file(self, f):
        """ Create the file f.
        """

        fullpath = os.path.join(self.project_path, f)
        create_missing_dirs(fullpath)
        open(fullpath, 'w').close()

    def _move_file(self, src, dest):
        """ Move the src path to the dest path.
        """

        src_fullpath = os.path.join(self.project_path, src)
        dest_fullpath = os.path.join(self.project_path, dest)

        shutil.move(src_fullpath, dest_fullpath)
        self.logger.debug("Moving %s to %s done." % (src_fullpath,
                                                     dest_fullpath))

    def _delete_file(self, f):
        """ Delete the file f from the project path.
        """

        fullpath = os.path.join(self.project_path, f)

        # Verifies if the current file exists on the filesystem
        # before delete it. For example, it can be already deleted
        # by a recursive deleted parent directory (with
        # shutil.rmtree below).
        if os.path.exists(fullpath):
            try:
                if os.path.isfile(fullpath):
                    # Remove the file.
                    os.remove(fullpath)

                    # Delete recursively all parent directories of
                    # the fullpath is they are empty.
                    self._clean_directory(self.project_path,
                                          os.path.dirname(fullpath))

                elif os.path.isdir(f):
                    shutil.rmtree(f)
                    self.logger.info('Directory recursively deleted: %s' % f)
            except OSError:
                # There's no problem if the file/dir does not
                # exists.
                pass

    def _get_hash(self, f):
        """ Computes the hash of the file f.
        """

        fullpath = os.path.join(self.project_path, f)

        # If the file has no write permission, set it.
        self._add_perm(fullpath, stat.S_IWUSR)

        # Verifies if all parent directories of the fullpath is created.
        create_missing_dirs(fullpath)

        # If the file does not exist, create it
        if not os.path.exists(fullpath):
            open(fullpath, 'w+b').close()

        if os.path.isfile(fullpath):
            # Computes the block checksums and add the result to the
            # all_hashes list.
            with open(fullpath, 'rb') as unpatched:
                return (f, pyrsync.blockchecksums(unpatched, blocksize=8192))

    def _send_hash(self, h):
        """ Sends over the transport streamer the hash h.
        """

        # Sets the future socket response dict.
        payload = {
            'sid': self.sid,
            'rid': self.rid,
            'node': self.project,
            'hashes': [h],
        }

        transport.streamer.send(self.sid, transport._pack(payload))

        # Wait until the rsync is finished.
        # TODO: It takes sometimes more than 240 sec (i.e. git pack files)
        self.rsync_finished.wait(240)

        if not self.rsync_finished.is_set():
            self.logger.error('Timeout on rsync detected !')

        # Reset the rsync_finished Event.
        self.rsync_finished.clear()

    def _get_hashes(self):
        """ Computes the delta hashes for each file in the files list
        and return the future rsync payload to send.
        """

        # Sets the future socket response dict.
        ret = {
            'sid': self.sid,
            'rid': self.rid
        }

        # A list of hashes.
        all_hashes = []

        for relpath in self.files:
            fullpath = os.path.join(self.project_path, relpath)

            # If the file has no write permission, set it.
            self._add_perm(fullpath, stat.S_IWUSR)

            # Verifies if all parent directories of the fullpath is
            # created.
            create_missing_dirs(fullpath)

            # If the file does not exist, create it
            if not os.path.exists(fullpath):
                open(fullpath, 'w+b').close()

            if os.path.isfile(fullpath):
                # Computes the block checksums and add the result to the
                # all_hashes list.
                with open(fullpath, 'rb') as unpatched:
                    hashes = pyrsync.blockchecksums(unpatched)
                    data = (relpath, hashes)
                    all_hashes.append(data)

        # Adds the hashes list in the ret dict.
        ret['hashes'] = all_hashes

        return ret

    def _add_perm(self, fullpath, perm):
        """ Add the permission (the list of available permissions is
        in the Python stat module) to the fullpath. If the fullpath
        does not exists, do nothing.
        """

        if os.path.exists(fullpath) and not os.access(fullpath, os.W_OK):
            cur_perm = stat.S_IMODE(os.stat(fullpath).st_mode)
            os.chmod(fullpath, cur_perm | stat.S_IWUSR)

    def _clean_directory(self, basepath, destpath):
        """ Deletes all empty directories from the destpath to
        basepath.
        """

        cur_dir = destpath
        while not cur_dir == basepath:
            try:
                os.rmdir(cur_dir)
                cur_dir = os.path.dirname(cur_dir)
            except OSError as e:
                if e.errno == errno.ENOTEMPTY:
                    # The directory is not empty. Return now.
                    return


@logger
class MergeTask(Task):
    """ A task to test if there's a conflict or not.
    """

    def __init__(self, project_name, username):
        """ Initialize the MergeTask.

        The project_name initializes the current working directory.

        The username is the user directory inside the project_name
        that indicates which user start the task.
        """

        # The priority is greater than EndTask and RsyncTask in order
        # to have a lower priority.
        super(MergeTask, self).__init__(5)

        # See the __init__ documentation.
        self.project_name = project_name
        self.username = username

        # Set the project cwd.
        self.project_cwd = os.path.join(config['server']['working_dir'],
                                        self.project_name)

        # Raise an error if the project cwd does not exist.
        if not os.path.exists(self.project_cwd):
            raise BaboonException('Cannot find the project on the server.'
                                  ' Are you sure %s is a correct project name'
                                  ' ?' % self.project_name)

        # Set the master user cwd.
        self.master_cwd = os.path.join(self.project_cwd, self.username)

        # Raise an error if the project cwd does not exist.
        if not os.path.exists(self.master_cwd):
            raise BaboonException('Cannot find the master user on the %s'
                                  ' project.' % self.project_name)

        # If the project cwd is mark as corrupted, stop this task.
        if os.path.exists(os.path.join(self.master_cwd, '.lock')):
            # The path exists -> the master_cwd is corrupted.
            raise BaboonException('The %s is corrupted. The merge task is'
                                  ' cancelled.' % self.master_cwd)

    def run(self):
        """ Test if there's a merge conflict or not.
        """

        # Verify if the repository of the master user is not locked.
        lock_file = os.path.join(self.master_cwd, '.baboon.lock')
        if os.path.exists(lock_file):
            self.logger.error("The %s directory is locked. Can't start a merge"
                              "task." % self.master_cwd)
            return

        self.logger.debug('Merge task %s started' % self.master_cwd)

        merge_threads = []

        # All users
        for user in self._get_user_dirs():
            try:
                # Create a thread by user to merge with the master
                # user repository.
                merge_thread = threading.Thread(target=self._user_side,
                                                args=(user, ))
                merge_thread.start()
                merge_threads.append(merge_thread)
            except BaboonException as e:
                self.logger.error(e)

        # Wait all merge threads are finished.
        for thread in merge_threads:
            thread.join()

        self.logger.debug('Merge task %s finished' % self.master_cwd)

    def _user_side(self, user):

        user_cwd = os.path.join(self.project_cwd, user)

        # If the user cwd is locked, stop the process.
        if os.path.exists(os.path.join(user_cwd, '.baboon.lock')):
            # The path exists -> the user_cwd is locke.
            self.logger.error('The %s is locked. Ignore it' % user_cwd)
            return

        # Add the master_cwd remote.
        exec_cmd('git remote add %s %s' % (self.username, self.master_cwd),
                 user_cwd)

        # Fetch the master_cwd repository.
        exec_cmd('git fetch %s' % self.username, user_cwd)

        # Get the current user branch
        _, out_branch, _ = exec_cmd('git symbolic-ref -q HEAD',
                                    self.master_cwd)

        # out_branch looks like something like :
        # refs/head/master\n. Parse it to only retrieve the branch
        # name.
        cur_branch = os.path.basename(out_branch).rstrip('\r\n')

        # Get the merge-base hash commit between the master user and the
        # current user.
        mergebase_hash = exec_cmd('git merge-base -a HEAD %s/%s' %
                                  (self.username, cur_branch),
                                  user_cwd)[1].rstrip('\r\n')

        # Get the diff between the master_cwd and the mergebase_hash.
        _, diff, _ = exec_cmd('git diff --binary --full-index %s' %
                              mergebase_hash, self.master_cwd)

        # Set the return code of the merge task to 0 by default. It means
        # there's no conflict.
        ret = 0

        # The future result string of the `git apply --check` command.
        patch_output = ""

        # If the diff is not empty, check if it can be applied in the user_cwd.
        # Otherwise, it means that there's no change, so there's no possible
        # conflict.
        if diff:
            # Create a temp file.
            tmpfile = tempfile.NamedTemporaryFile()
            try:
                # Write the diff into a temp file.
                tmpfile.write(diff)
                # After writing, rewind the file handle using seek() in order
                # to read the data back from it.
                tmpfile.seek(0)

                # Check if the diff can be applied in the master user.
                ret, patch_output, _ = exec_cmd('git apply --check %s' %
                                                tmpfile.name, user_cwd)
            finally:
                # Automatically delete the temp file.
                tmpfile.close()

        # Build the *args for the _alert method.
        alert_args = (self.project_name, self.username, user)

        # Build the **kwargs for the _alert method if there's no
        # conflict.
        alert_kwargs = {'merge_conflict': False, }

        if ret:
            # Build the **kwargs for the _alert method if there's a
            # merge conflict.x
            alert_kwargs = {
                'merge_conflict': True,
                'conflict_files': self._get_conflict_files(patch_output)
            }

        # Call the _alert method with alert_args tuple as *args
        # argument and alert_kwargs dict as **kwargs.
        self._alert(*alert_args, **alert_kwargs)

    def _get_conflict_files(self, patch_output):
        """ Parses the patch_output string and returns a readable list of
        conflict files.
        """

        conflict_files = []
        for i, line in enumerate(patch_output.split('\n')):
            if not i % 2:
                conflict_files.append(line)

        return conflict_files

    def _alert(self, project_name, username, dest_username,
               merge_conflict=False, conflict_files=[]):
        """ Creates a alert task to warn to the user the state of the
        merge.
        """

        dispatcher.put(project_name, AlertTask(project_name, username,
                                               dest_username, merge_conflict,
                                               conflict_files=conflict_files))

    def _get_user_dirs(self):
        """ A generator that returns the next user directory in the
        self.project_cwd.
        """

        for folder_name in os.listdir(self.project_cwd):
            folder_fullpath = os.path.join(self.project_cwd, folder_name)
            if folder_fullpath != self.master_cwd and \
                    os.path.isdir(folder_fullpath):
                yield folder_name
