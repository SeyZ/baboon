import sys

from threading import Thread

if sys.version_info < (3, 0):
    from Queue import PriorityQueue
else:
    from queue import PriorityQueue

from baboon.common.logger import logger
from baboon.common.errors.baboon_exception import BaboonException


@logger
class Executor(Thread):
    """ This class applies the baboonsrv workflow task by task.
    """

    def __init__(self):
        """ Initialize the executor thread. Executor has only ONE
        thread because all the task MUST BE executed one after
        another.
        """

        Thread.__init__(self)

        # A priority queue to store all tasks. The priority is important in
        # order to have an endtask with high priority. When someone puts an
        # EndTask into this queue, the next task will be that and all other
        # tasks will be ignored.
        self.tasks = PriorityQueue()

    def run(self):
        """ Consume on the tasks queue and run each task until an
        endtask.
        """
        from baboon.baboond.task import EndTask

        # The endtask is a flag to indicate if it's the end of life of
        # the server or not.
        endtask = False

        # While the endtask is False, continue to consume on the
        # queue.
        while not endtask:
            # Take the next task...
            task = self.tasks.get()

            # Verify that it's not a EndTask.
            endtask = type(task) == EndTask

            # Run it !
            try:
                self.logger.debug('Running a new task...')
                task.run()
            except BaboonException as err:
                self.logger.error(err)

            # Mark the task finished
            self.logger.debug('A task has been finished...')
            self.tasks.task_done()
            self.logger.debug('Remaining task(s): %s' % self.tasks.qsize())

        self.logger.debug('The executor thread is now finished.')
