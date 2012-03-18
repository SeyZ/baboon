import os
import fnmatch
from monitor import EventHandler


class EventHandlerGit(EventHandler):
    @property
    def scm_name(self):
        return 'git'

    def exclude_paths(self):
        excl = ['.*\.git.*']

        gitignore = os.path.join(self.config.path, '.gitignore')
        if os.path.exists(gitignore):
            with open(gitignore, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    regexp = fnmatch.translate(line)
                    excl.append(regexp)

        return excl
