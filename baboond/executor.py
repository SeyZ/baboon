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

        self.logger.info('Ending')


class Preparator():
    """ The preparator builds the task and put it in the tasks queue.
    """

    # Stores the rsync task in a dict:
    # Key: req_id
    # Value: RsyncTask
    rsync_tasks = {}

    def prepare_rsync_start(self):
        """ Prepares the beginning of a new rsync task.
        """

        # Create the rsync task.
        rsync_task = RsyncTask()
        tasks.put(rsync_task)

        # Associate a uuid to the rsync task and store it into
        # rsync_tasks dict.
        req_id = str(uuid.uuid4())
        self.rsync_tasks[req_id] = rsync_task

        # TODO - Permission !
        # Return all the necessary information to the baboon client.
        ret = {'req_id': req_id,
               'remote_dir': 'root@%s:/tmp/%s/%s/' % \
                   (config.baboonsrv_host, config.node, config.jid)
               }

        # Return the dict
        return ret

    def prepare_rsync_stop(self, req_id):
        """ The rsync transaction with the req_id and prepares a new
        rsync stop task to warn the associated rsync_task it's
        completed.
        """

        try:
            # Gets the rsync task in the rsync_tasks dict with the
            # req_id key.
            rsync_task = self.rsync_tasks.pop(req_id)

            # Throws the event to warn the rsync is now completed.
            rsync_task.ready.set()

            # Returns True to say the request is correctly completed.
            return True
        except KeyError:
            self.logger.debug("Cannot find the rsync transaction with the key"
                              " %s" % req_id)

            # Returns False because the request cannot be completed
            # due to the bad req_id.
            return False

    def prepare_merge_verification(self, **kwargs):
        """ Prepares a new merge verification task.
        """

        try:
            # Gets useful data from kwargs
            node = kwargs.get('node')
            username = kwargs.get('username')

            # Creates the new merge task
            new_task = MergeTask(node, username)
            tasks.put(new_task)

            return True

        except KeyError:
            return False

preparator = Preparator()
