import os
import fnmatch

from monitor import EventHandler


class EventHandlerGit(EventHandler):
    @property
    def scm_name(self):
        return 'git'

    def exclude_paths(self):
        excl = ['.*\.git.*']
        gitignore_files = self._parse_gitignore()
        if gitignore_files != None:
            excl += gitignore_files

        return excl

    def _parse_gitignore(self):
        """ Parse the .gitignore file in the repository and return a
        list of all ignored patterns
        """
        gitignore_path = os.path.join(self.config.path, '.gitignore')
        lines = []  # contains each line of the .gitignore file
        results = []  # contains the result regexp patterns

        with open(gitignore_path, 'r') as f:
            lines = f.readlines()

        # Sort the line in order to have inverse pattern first
        lines.sort(self._gitline_comparator)

        # For each git pattern, convert it to regexp pattern
        for line in lines:
            results.append(self._gitline_to_regexp(line))

        return results

    def _gitline_comparator(self, a, b):
        """ Compares a and b. I want to have pattern started with '!'
        firstly
        """
        if a.startswith('!'):
            return -1
        elif b.startswith('!'):
            return 1
        else:
            return a == b

    def _gitline_to_regexp(self, line):
        """ Convert the unix pattern (line) to a regex pattern
        """
        negation = False  # if True, inverse the pattern

        # Remove the dirty characters like spaces at the beginning
        # or at the end, carriage returns, etc.
        line = line.strip()

        # A blank line matches no files, so it can serve as a
        # separator for readability.
        if line == '':
            return

        # A line starting with # serves as a comment.
        if line.startswith('#'):
            return

        # An optional prefix !  which negates the pattern; any
        # matching file excluded by a previous pattern will become
        # included again. If a negated pattern matches, this will
        # override
        if line.startswith('!'):
            negation = True

        # If the pattern does not contain a slash /, git treats it
        # as a shell glob pattern and checks for a match against
        # the pathname relative to the location of the .gitignore
        # file (relative to the toplevel of the work tree if not
        # from a .gitignore file).

        # Otherwise, git treats the pattern as a shell glob
        # suitable for consumption by fnmatch(3) with the
        # FNM_PATHNAME flag: wildcards in the pattern will not
        # match a / in the pathname. For example,
        # "Documentation/*.html" matches "Documentation/git.html"
        # but not "Documentation/ppc/ppc.html" or
        # "tools/perf/Documentation/perf.html".
        regex = fnmatch.translate(line)
        regex = regex.replace('\\Z(?ms)', '')

        if negation:
            regex = '(?!%s)' % regex

        regex = '.*%s.*' % regex

        return regex
