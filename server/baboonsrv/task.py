import os
import subprocess
import executor

from threading import Event
from alert import Xmpp
from errors.baboon_exception import BaboonException

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
        # Nothing to do. This class is just a sort of flag with high
        # priority.

        pass


class AlertTask(Task):
    """ A high priority task to alert baboon client the state of the
    merge.
    """

    xmpp = Xmpp()

    def __init__(self, merge_conflict=False):
        """ Initialize the AlertTask. By default, there's no merge
        conflict.
        """

        # The priority is 2. It means that it's the higher possible
        # priority for baboonsrv except the EndTask.
        super(AlertTask, self).__init__(2)

        self.merge_conflict = merge_conflict

    def run(self):
        msg = 'Conflict detected' if self.merge_conflict else \
            'Everything seems to be perfect'
        self.xmpp.alert(msg)


class RsyncTask(Task):
    """ A task to rsync the local repository of the baboon client and
    the server.
    """

    def __init__(self):
        """ Initialize the RsyncTask
        """

        # The priority is lower than MergeTask in order to have a
        # higher priority.
        super(RsyncTask, self).__init__(3)

        self.ready = Event()

    def run(self):
        print 'Wait rsync... !'
        self.ready.wait()
        print 'The rsync is finished !'


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

    def run(self):
        """ Test if there's a merge conflict or not.
        """

        # Master user
        self._exec_cmd('git add *')
        self._exec_cmd('git commit -am "Baboon commit"')

        # All users
        for user in self._get_user_dirs():
            self._user_side(user)

        self._exec_cmd('git reset HEAD~1')

    def _user_side(self, user):

        user_cwd = os.path.join(self.project_cwd, user)

        self._exec_cmd('git remote add %s %s' %
                       (self.username, self.master_cwd), user_cwd)
        self._exec_cmd('git add *', user_cwd)
        self._exec_cmd('git commit -am "Baboon commit"', user_cwd)
        self._exec_cmd('git fetch %s' % self.username, user_cwd)
        ret = self._exec_cmd('git merge %s/master --no-commit --no-ff' %
                             self.username, user_cwd)
        self._exec_cmd('git merge --abort', user_cwd)
        self._exec_cmd('git reset HEAD~1', user_cwd)

        if ret != 0:
            self._alert(True)
        else:
            # merge_conflict = False
            self._alert()

    def _alert(self, merge_conflict=False):
        """ Creates a alert task to warn to the user the state of the
        merge.
        """

        alertTask = AlertTask(merge_conflict)
        executor.tasks.put(alertTask)

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
