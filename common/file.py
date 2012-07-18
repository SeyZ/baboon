

class FileEvent(object):
    """ Describes a file event. Avoid to use watchdog event to have relpaths
    instead of fullpaths. In addition, if watchdog is replaced by another
    library, the rest of the code will not need to change.
    """

    pending = []

    CREATE = 0
    MODIF = 1
    MOVE = 2
    DELETE = 3

    def __init__(self, event_type, src_path, dest_path=None):
        """
        """

        self.event_type = event_type
        self.src_path = src_path
        self.dest_path = dest_path

    def register(self):
        self.pending.append(self)
