import os
import subprocess
import executor

from threading import Event
from transport import transport
from common.logger import logger
from common.errors.baboon_exception import BaboonException

WORKING_DIR = '/tmp'


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

    def __init__(self, project_name, username, merge_conflict=False):
        """ Initialize the AlertTask. By default, there's no merge
        conflict.
        """

        # The priority is 2. It means that it's the higher possible
        # priority for baboonsrv except the EndTask.
        super(AlertTask, self).__init__(2)

        self.project_name = project_name
        self.username = username
        self.merge_conflict = merge_conflict

    def run(self):
        msg = 'Conflict detected' if self.merge_conflict else \
            'Everything seems to be perfect'
        transport.alert(self.project_name, self.username, msg)


@logger
class RsyncTask(Task):
    """ A task to rsync the local repository of the baboon client and
    the server.
    """

    def __init__(self, project_name, username):
        """ Initialize the RsyncTask
        """

        # The priority is lower than MergeTask in order to have a
        # higher priority.
        super(RsyncTask, self).__init__(3)

        self.project_name = project_name
        self.username = username

        self.ready = Event()

    def run(self):
        self.logger.info("Wait rsync... !")

        # Times out after the <arg> second(s).
        no_timeout = self.ready.wait(30)

        # If the no_timeout is False, it means the request was too
        # long.
        if no_timeout is False:
            # The user's repository on the server can be
            # corrupted. So, marks the repository to be in corrupted
            # mode.
            executor.preparator.prepare_corrupted(self.project_name,
                                                  self.username)
            raise BaboonException('The rsync request takes too long time.')
        else:
            self.logger.info("The rsync is finished !")

            # If the repository was corrupted, remove the .lock file
            # to say it's now good.
            cwd = os.path.join(WORKING_DIR, self.project_name, self.username)
            cwd_lock = os.path.join(cwd, '.lock')
            if os.path.exists(cwd_lock):
                os.remove(cwd_lock)
                self.logger.debug("The %s directory was corrupted. It's now"
                                  " fixed." % cwd)


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
        project_dir = os.path.join(WORKING_DIR,
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
        self.project_cwd = os.path.join(WORKING_DIR, self.project_name)

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

        # Master user
        self._exec_cmd('git add -A')
        self._exec_cmd('git commit -am "Baboon commit"')

        # All users
        for user in self._get_user_dirs():
            try:
                self._user_side(user)
            except BaboonException, e:
                self.logger.error(e)

        self._exec_cmd('git reset HEAD~1')

    def _user_side(self, user):

        user_cwd = os.path.join(self.project_cwd, user)

        # If the user cwd is mark as corrupted, stop the process.
        if os.path.exists(os.path.join(user_cwd, '.lock')):
            # The path exists -> the user_cwd is corrupted.
            raise BaboonException('The %s is corrupted. Ignore it' % user_cwd)

        self._exec_cmd('git remote add %s %s' %
                       (self.username, self.master_cwd), user_cwd)
        self._exec_cmd('git add -A', user_cwd)
        self._exec_cmd('git commit -am "Baboon commit"', user_cwd)
        self._exec_cmd('git fetch %s' % self.username, user_cwd)
        ret = self._exec_cmd('git merge %s/master --no-commit --no-ff' %
                             self.username, user_cwd)
        self._exec_cmd('git merge --abort', user_cwd)
        self._exec_cmd('git reset HEAD~1', user_cwd)

        if ret != 0:
            self._alert(self.project_name, self.username, True)
        else:
            # merge_conflict = False
            self._alert(self.project_name, self.username)

    def _alert(self, project_name, username, merge_conflict=False):
        """ Creates a alert task to warn to the user the state of the
        merge.
        """

        executor.preparator.prepare_alert(project_name,
                                          username,
                                          merge_conflict)

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
        proc.communicate()

        if proc.returncode != 0:
            # TODO: raise an error !
            pass

        return proc.returncode
