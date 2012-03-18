from monitor import EventHandler


class EventHandlerHg(EventHandler):
    @property
    def scm_name(self):
        return 'hg'

    def exclude_paths(self):
        return ['.*\.hg.*', '.*hg-check.*']
