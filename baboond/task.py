import os
import errno
import stat
import subprocess
import threading
import shutil

import pyrsync
import executor

from transport import transport
from common.file import FileEvent
from common.logger import logger
from common.errors.baboon_exception import BaboonException
from config import config


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
        """ Initialize the EndTask.
        """

        # The priority is 1. It means that it's the higher possible
        # priority for baboonsrv.
        super(EndTask, self).__init__(1)

    def run(self):
        # Shutdowns Baboond.

        # Closes the transport
        transport.close()

        # Bye !
        self.logger.info('Bye !')


class AlertTask(Task):
    """ A high priority task to alert baboon client the state of the
    merge.
    """

    def __init__(self, project_name, username, merge_conflict=False,
                 conflict_files=[]):
        """ Initialize the AlertTask. By default, there's no merge
        conflict.
        """

        # The priority is 2. It means that it's the higher possible
        # priority for baboonsrv except the EndTask.
        super(AlertTask, self).__init__(2)

        self.project_name = project_name
        self.username = username
        self.merge_conflict = merge_conflict
        self.conflict_files = conflict_files

    def run(self):
        msg = 'Everything seems to be perfect'

        if self.merge_conflict:
            msg = 'Conflict detected in: '
            for f in self.conflict_files:
                msg += f + ', '

        transport.alert(self.project_name, self.username, msg)


@logger
class RsyncTask(Task):
    """ A rsync task to sync the baboon client repository with
    relative repository server-side.
    """

    def __init__(self, sid, rid, sfrom, project_path, files):

        super(RsyncTask, self).__init__(3)

        self.sid = sid
        self.rid = rid
        self.sfrom = sfrom
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

        for f in self.files:
            if f.event_type == FileEvent.CREATE:
                self.logger.info('[%s] - Need to create %s.' %
                    (self.project_path, f.src_path))
                self._create_file(f.src_path)
            elif f.event_type == FileEvent.MODIF:
                self.logger.info('[%s] - Need to sync %s.' %
                    (self.project_path, f.src_path))
                new_hash = self._get_hash(f.src_path)
                self._send_hash(new_hash)
            elif f.event_type == FileEvent.DELETE:
                self.logger.info('[%s] - Need to delete %s.' %
                        (self.project_path, f.src_path))
                self._delete_file(f.src_path)
            elif f.event_type == FileEvent.MOVE:
                self.logger.info('[%s] - Need to move %s to %s.' %
                    (self.project_path, f.src_path, f.dest_path))
                self._move_file(f.src_path, f.dest_path)

        # TODO: Remove the rsync_task in the pending_rsyncs dict of the
        # transport.
        self.logger.debug('Rsync task %s finished', self.sid)

    def _create_file(self, f):
        """ Create the file f.
        """

        fullpath = os.path.join(self.project_path, f)
        self._create_missing_dirs(fullpath)
        open(fullpath, 'w').close()

    def _move_file(self, src, dest):
        src_fullpath = os.path.join(self.project_path, src)
        dest_fullpath = os.path.join(self.project_path, dest)

        shutil.move(src_fullpath, dest_fullpath)
        self.logger.info('Move done !')

    def _delete_file(self, f):

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
                    self.logger.info('Directory recursively deleted: %s' \
                                         % f)
            except OSError:
                # There's no problem if the file/dir does not
                # exists.
                pass

    def _get_hash(self, f):
        fullpath = os.path.join(self.project_path, f)

        # If the file has no write permission, set it.
        self._add_perm(fullpath, stat.S_IWUSR)

        # Verifies if all parent directories of the fullpath is
        # created.
        self._create_missing_dirs(fullpath)

        # If the file does not exist, create it
        if not os.path.exists(fullpath):
            open(fullpath, 'w+b').close()

        if os.path.isfile(fullpath):
            # Computes the block checksums and add the result to the
            # all_hashes list.
            with open(fullpath, 'rb') as unpatched:
                return (f, pyrsync.blockchecksums(unpatched))

    def _send_hash(self, h):
        # Sets the future socket response dict.
        payload = {
            'sid': self.sid,
            'rid': self.rid,
            'hashes': [h],
        }

        transport.streamer.send(self.sid, transport._pack(payload))

        # Wait until the rsync is finished.
        self.rsync_finished.wait(60)

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
            self._create_missing_dirs(fullpath)

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

    def _create_missing_dirs(self, fullpath):
        """ Creates all missing parent directories of the fullpath.
        """

        if not os.path.exists(os.path.dirname(fullpath)):
            try:
                # Creates all the parent directories.
                os.makedirs(os.path.dirname(fullpath))
            except OSError:
                pass

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
class CorruptedTask(Task):
    """ A task to mark a repository in corrupted mode.
    """

    def __init__(self, project_name, username):
        """ Initializes the corrupted task with the higher possible
        priority.
        """

        super(CorruptedTask, self).__init__(0)

        self.project_name = project_name
        self.username = username

    def run(self):
        """ Marks the directory of the project_name/username as
        corrupted.
        """

        # Gets the project directory
        project_dir = os.path.join(config.working_dir,
                                   self.project_name,
                                   self.username)

        # Writes a .lock file in the directory to say the directory is
        # corrupted.
        with open(os.path.join(project_dir, '.lock'), 'w'):
            pass

        self.logger.error('The repository %s is mark as corrupted.' %
                          project_dir)


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
        super(MergeTask, self).__init__(4)

        # See the __init__ documentation.
        self.project_name = project_name
        self.username = username

        # Set the project cwd.
        self.project_cwd = os.path.join(config.working_dir, self.project_name)

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

        self.logger.debug('Merge task %s started' % self.master_cwd)

        gitdir = os.path.join(self.master_cwd, '.git')
        import uuid
        destdir = "/tmp/%s" % uuid.uuid4()
        shutil.copytree(gitdir, destdir)

        # Master user
        self._exec_cmd('git add -A')
        ret_code = self._exec_cmd('git commit -am "Baboon commit"')[0]

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
            except BaboonException, e:
                self.logger.error(e)

        # Wait all merge threads are finished.
        for thread in merge_threads:
            thread.join()

        if not ret_code:
            # Reset the master user repository.
            self._exec_cmd('git reset HEAD~1')
            shutil.rmtree(gitdir)
            shutil.move(destdir, gitdir)

        self.logger.debug('Merge task %s finished' % self.master_cwd)

    def _user_side(self, user):

        user_cwd = os.path.join(self.project_cwd, user)

        # If the user cwd is mark as corrupted, stop the process.
        if os.path.exists(os.path.join(user_cwd, '.lock')):
            # The path exists -> the user_cwd is corrupted.
            raise BaboonException('The %s is corrupted. Ignore it' % user_cwd)

        # Add the master_cwd remote.
        self._exec_cmd('git remote add %s %s' %
                       (self.username, self.master_cwd), user_cwd)

        # Stage all the working directory.
        self._exec_cmd('git add -A', user_cwd)

        # Do a Baboon commit.
        self._exec_cmd('git commit -am "Baboon commit"', user_cwd)

        # Fetch the master_cwd repository.
        self._exec_cmd('git fetch %s' % self.username, user_cwd)

        # Get the current user branch
        out_branch = self._exec_cmd('git symbolic-ref -q HEAD')[1]

        # out_branch looks like something like :
        # refs/head/master\n. Parse it to only retrieve the branch
        # name.
        cur_branch = os.path.basename(out_branch).replace('\n', '')

        # Merge the master branch in the current user repository. If
        # the merge is well, ret equals 0.
        ret = self._exec_cmd('git merge %s/%s --no-commit --no-ff' % \
                                 (self.username, cur_branch), user_cwd)[0]

        # Build the *args for the _alert method.
        alert_args = (self.project_name, self.username)

        # Build the **kwargs for the _alert method if there's no
        # conflict.
        alert_kwargs = {'merge_conflict': False, }

        if ret:
            # There's a merge conflict. Get the list of conflict
            # files.
            conflict_files = self._exec_cmd('git ls-files -u | cut -f 2 | '
                                            'sort -u', user_cwd)[1].split()

            # Build the **kwargs for the _alert method if there's a
            # merge conflict.x
            alert_kwargs = {
                'merge_conflict': True,
                'conflict_files': conflict_files
                }

        # Go to the normal situation.
        self._exec_cmd('git merge --abort', user_cwd)
        self._exec_cmd('git reset HEAD~1', user_cwd)

        # Call the _alert method with alert_args tuple as *args
        # argument and alert_kwargs dict as **kwargs.
        self._alert(*alert_args, **alert_kwargs)

    def _alert(self, project_name, username, merge_conflict=False,
               conflict_files=[]):
        """ Creates a alert task to warn to the user the state of the
        merge.
        """

        executor.preparator.prepare_alert(project_name,
                                          username,
                                          merge_conflict,
                                          conflict_files)

    def _get_user_dirs(self):
        """ A generator that returns the next user directory in the
        self.project_cwd.
        """

        for folder_name in os.listdir(self.project_cwd):
            folder_fullpath = os.path.join(self.project_cwd, folder_name)
            if folder_fullpath != self.master_cwd and \
                    os.path.isdir(folder_fullpath):
                yield folder_name

    def _exec_cmd(self, cmd, cwd=None):
        """ Execute the cmd command in a subprocess. Returns the
        returncode.
        """

        # Shlex the cmd.
        #cmd = shlex.split(cmd)

        # If cwd is None, set cwd to self.master_cwd.
        if cwd is None:
            cwd = self.master_cwd

        # Open a subprocess
        proc = subprocess.Popen(cmd,
                                stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                shell=True,
                                cwd=cwd
                                )
        # Run the command
        output, errors = proc.communicate()

        if proc.returncode != 0:
            # TODO: raise an error !
            pass

        return (proc.returncode, output, errors)
