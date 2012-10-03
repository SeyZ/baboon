
pending = {}


class FileEvent(object):
    """ Describes a file event. Avoid to use watchdog event to have relpaths
    instead of fullpaths. In addition, if watchdog is replaced by another
    library, the rest of the code will not need to change.
    """

    CREATE = 0
    MODIF = 1
    MOVE = 2
    DELETE = 3

    def __init__(self, project, event_type, src_path, dest_path=None):
        """
        """

        self.project = project
        self.event_type = event_type
        self.src_path = src_path
        self.dest_path = dest_path

    def register(self):

        if not pending.get(self.project):
            pending[self.project] = []

        if hash(self) not in [hash(x) for x in pending[self.project]]:
            pending[self.project].append(self)

    def __hash__(self):
        return (hash(self.project) ^
                hash(self.event_type) ^
                hash(self.src_path) ^
                hash(self.dest_path))
