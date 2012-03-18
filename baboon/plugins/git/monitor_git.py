from monitor import Monitor


class EventHandlerGit(Monitor):
    @property
    def scm_name(self):
        return 'git'

    def exclude_paths(self):
        return ['.*\.git.*']
