from executor import Executor

from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


@logger
class Dispatcher(object):
    """ This class has the responsability to dispatch tasks to the good
    executor thread according to the project name.
    """

    def __init__(self):
        """
        """

        # Keys -> project name, Values -> The associated executor thread.
        self.executors = {}

    def put(self, project_name, task):
        """ Put the task to the executor thread associated to the project name.
        If the thread does not exist, it will be created.
        """

        # Get the executor thread associated to the project name.
        executor = self.executors.get(project_name)
        if not executor:
            # The thread does not exist yet. Create a new one.
            executor = Executor()

            # Associate this new thread to the project_name.
            self.executors[project_name] = executor

            # Start the thread.
            executor.start()

        # Put the task to the good executor thread.
        executor.tasks.put(task)

    def close(self):
        """ Stop all executor threads.
        """

        from baboon.baboond.task import EndTask

        for executor in self.executors.values():
            executor.tasks.put(EndTask())
            executor.join()


dispatcher = Dispatcher()
