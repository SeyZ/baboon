from monitor import EventHandler


class EventHandlerGit(EventHandler):
    @property
    def scm_name(self):
        return 'git'

    def exclude_paths(self):
        return ['.*\.git.*']
