import os
import subprocess
import shlex
import executor

from transport import transport
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
