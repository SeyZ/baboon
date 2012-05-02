import uuid
from task import RsyncTask, MergeTask
from executor import tasks
from bottle import route, request, HTTPError


@route('/tasks', method='GET')
def get_pending_tasks():
    return "Not implemented yet."


rsync_tasks = {}


@route('/tasks/rsync_request', method='POST')
def rsync_request():
    """ Create a rsync task and wait until the DELETE http method is
    called on the same url to continue.
    """

    project_name = request.params.project_name
    username = request.params.username
    server_host = request.params.server_host

    # Create the rsync task.
    rsync_task = RsyncTask()
    tasks.put(rsync_task)

    # Associate a uuid to the rsync task and store it into rsync_tasks
    # dict.
    req_id = str(uuid.uuid4())
    rsync_tasks[req_id] = rsync_task

    # Return all the necessary information to the baboon client.
    ret = {'req_id': req_id,
           'remote_dir': 'root@%s:/tmp/%s/%s/' % \
               (server_host, project_name, username)
           }

    # Return the dict
    return ret


@route('/tasks/rsync_request/:req_id', method='DELETE')
def rsync_request_finished(req_id):
    """ Throw an event to say the rsync_task associated to the
    req_id is finished.
    """

    try:
        rsync_task = rsync_tasks[req_id]

        # Throw the event.
        rsync_task.ready.set()
    except:
        raise HTTPError

    return 'OK\n'


@route('/tasks', method='POST')
def create_task():
    project_name = request.params.project_name
    username = request.params.username

    if not project_name or not username:
        # error
        return "Error"

    new_task = MergeTask(project_name, username)
    tasks.put(new_task)

    return 'OK\n'
