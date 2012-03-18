from monitor import EventHandler


class EventHandlerGit(EventHandler):
    @property
    def scm_name(self):
        return 'git'

    def exclude_paths(self):
        excl = ['.*\.git.*']
        gitignore_files = self._parse_gitignore()
        if gitignore_files != None:
            excl.append(gitignore_files)

        return excl

    def _parse_gitignore(self):
        """ Parse the .gitignore file in the repository and return a
        list of all ignored patterns
        """
        # TODO: implement this method !
        return
