import os
import fnmatch
from monitor import EventHandler


class EventHandlerHg(EventHandler):
    @property
    def scm_name(self):
        return 'hg'

    def exclude_paths(self):
        excl = ['.*\.hg.*', '.*hg-check.*']

        hgignore_files = self._parse_hgignore()
        if hgignore_files is not None:
            excl += hgignore_files

        return [], excl

    def _parse_hgignore(self):
        """ Parses the .hgignore file in the repository. Returns a
        list of patterns
        """
        hgignore_path = os.path.join(self.config.path, '.hgignore')
        lines = []  # contains each line of the .hgignore file
        results = []  # contains the result regexp patterns

        #  Mercurial supports several pattern syntaxes.  The default
        #  syntax used is Python/Perl-style regular expressions.
        syntax = 'regexp'

        with open(hgignore_path, 'r') as f:
            lines = f.readlines()

        for line in lines:
            # Mercurial supports several pattern syntaxes. The default
            # syntax used is Python/Perl-style regular expressions.
            # To change the syntax used, use a line of the following
            # form:
            #
            # syntax: NAME
            #
            # where NAME is one of the following:
            # regexp
            #     Regular expression, Python/Perl syntax.
            # glob
            #     Shell-style glob.
            new_syntax = self._get_hgignore_syntax(line)
            if new_syntax is not None:
                syntax = new_syntax
            else:
                if syntax == 'regexp':
                    results += line
                elif syntax == 'glob':
                    results += fnmatch.translate(line)

    def _get_hgignore_syntax(self, line):
        syntax = None

        if line.startswith('syntax'):
            syntax = line.split('syntax')
            # Trying to detect the : character to have the good
            # syntax name according to the hgignore manpage
            try:
                syntax = syntax.split(':')[1]
                # Strip all dirty characters
                syntax = syntax.strip()
            except IndexError:
                # If a IndexError is raised, it's not a 'syntax' valid
                # pattern according to the hgignore manpage. It should be
                # a pattern as another.
                return None

        return syntax
