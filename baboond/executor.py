import uuid

from threading import Thread
from Queue import PriorityQueue

from task import EndTask, RsyncTask, MergeTask
from config import config
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


class Preparator():
    """
    """

    rsync_tasks = {}

    def prepare_rsync_start(self):
        # Create the rsync task.
        rsync_task = RsyncTask()
        tasks.put(rsync_task)

        # Associate a uuid to the rsync task and store it into
        # rsync_tasks dict.
        req_id = str(uuid.uuid4())
        self.rsync_tasks[req_id] = rsync_task

        # TODO - Remove hard coded information
        # Return all the necessary information to the baboon client.
        ret = {'req_id': req_id,
               'remote_dir': 'root@%s:/tmp/%s/%s/' % \
                   (config.baboonsrv_host, config.node, config.jid)
               }

        # Return the dict
        return ret

    def prepare_rsync_stop(self, req_id):
        rsync_task = self.rsync_tasks[req_id]

        # Throw the event.
        rsync_task.ready.set()

        return True

    def prepare_merge_verification(self, data):
        new_task = MergeTask(data['node'], data['username'])
        tasks.put(new_task)

preparator = Preparator()
