

class EventBus(object):
    """
    """

    def __init__(self):

        # The dict that associate a key (the event) and a callback.
        self._handlers = {}

        # A list of callbacks that will be removed after the first call.
        self._oneshot_callbacks = set()

    def register(self, key, callback):
        if not self._handlers.get(key):
            self._handlers[key] = set()

        self._handlers[key].add(callback)

    def register_once(self, key, callback):
        """ Associates the key to the callback. The callback will be
        automatically unregister after the call.
        """
        self.register(key, callback)
        self._oneshot_callbacks.add(callback)

    def unregister(self, key, callback):
        try:
            filter(lambda x: x is not callback, self._handlers[key])
            filter(lambda x: x is not callback, self._oneshot_callbacks)
        except KeyError:
            pass

    def fire(self, key, *args, **kwargs):
        try:
            for callback in self._handlers[key]:
                callback(*args, **kwargs)
                self.unregister(key, callback)

        except KeyError:
            pass

eventbus = EventBus()
