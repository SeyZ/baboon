import os
import re
import fnmatch

from monitor import EventHandler


class EventHandlerHg(EventHandler):
    def __init__(self, transport, diffman):
        super(EventHandlerHg, self).__init__(transport, diffman)
        # My ignore file name is...
        self.hgignore_path = os.path.join(self.config.path, '.hgignore')

        # List of compiled RegExp objects

        # Always ignore the .hg directory. In addition, mercurial
        # generates temporary files that match *hg-check* pattern. We
        # need to ignore it too.
        self.exclude_regexps = [re.compile('.*\.hg.*'),
                                re.compile('.*hg-check.*')]
        # Update those lists
        self._populate_hgignore_items()

    @property
    def scm_name(self):
        return 'hg'

    def _populate_hgignore_items(self):
        hgignore_items = self._parse_hgignore()
        if hgignore_items != None:
            # Let's compile them already :)
            self.exclude_regexps += [re.compile(x) for x in hgignore_items]

    def exclude(self, rel_path):
        # First, check if the modified file is the hgignore file. If it's the
        # case, update include/exclude paths lists.
        if rel_path == self.hgignore_path:
            self._populate_hgignore_items()

        return self._match_excl_regexp(rel_path)

    def _match_excl_regexp(self, rel_path):
        for regexp in self.exclude_regexps:
            if regexp.search(rel_path) is not None:
                self.logger.debug("The path %s matches the ignore regexp"
                                  " %s." % (rel_path, regexp.pattern))
                return True
        return False

    def _parse_hgignore(self):
        """ Parses the .hgignore file in the repository. Returns a
        list of patterns
        """
        lines = []  # contains each line of the .hgignore file
        results = []  # contains the result regexp patterns

        # Mercurial supports several pattern syntaxes.  The default
        # syntax used is Python/Perl-style regular expressions.
        syntax = 'regexp'

        with open(self.hgignore_path, 'r') as f:
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

        return results

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
