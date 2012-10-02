from threading import Thread
from Queue import PriorityQueue

from baboond.task import EndTask
from common.logger import logger
from common.errors.baboon_exception import BaboonException

# A priority queue to store all tasks. The priority is important in
# order to have an endtask with high priority. When someone puts an
# EndTask into this queue, the next task will be that and all other
# tasks will be ignored.
tasks = PriorityQueue()


@logger
class Scheduler(Thread):
    """ This class applies the baboonsrv workflow task by task.
    """

    def __init__(self):
        """ Initialize the executor thread. Executor has only ONE
        thread because all the task MUST BE executed one after
        another.
        """

        Thread.__init__(self)

    def run(self):
        """ Consume on the tasks queue and run each task until an
        endtask.
        """

        self.logger.info('Running')

        # The endtask is a flag to indicate if it's the end of life of
        # the server or not.
        endtask = False

        # While the endtask is False, continue to consume on the
        # queue.
        while not endtask:
            # Take the next task...
            task = tasks.get()

            # Verify that it's not a EndTask.
            endtask = type(task) == EndTask

            # Run it !
            try:
                task.run()
            except BaboonException as err:
                self.logger.error(err)

            # Mark the task finished
            tasks.task_done()

        self.logger.debug('The executor thread is now finished.')
