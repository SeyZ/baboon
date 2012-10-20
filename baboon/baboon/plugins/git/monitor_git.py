import os
import sys
import re
import fnmatch

if sys.version_info < (2, 7):
    # Python < 2.7 doesn't have the cmp_to_key function.
    from baboon.common.utils import cmp_to_key
else:
    from functools import cmp_to_key

from baboon.baboon.monitor import EventHandler
from baboon.common.errors.baboon_exception import BaboonException


class EventHandlerGit(EventHandler):
    def __init__(self, project_path):
        super(EventHandlerGit, self).__init__(project_path)

        # My ignore file name is...
        self.gitignore_path = os.path.join(project_path, '.gitignore')

        # Lists of compiled RegExp objects
        self.include_regexps = []
        self.exclude_regexps = []

        # Update those lists
        self._populate_gitignore_items()

    @property
    def scm_name(self):
        return 'git'

    def exclude(self, rel_path):
        # First, check if the modified file is the gitignore file. If it's the
        # case, update include/exclude paths lists.
        if rel_path == self.gitignore_path:
            self._populate_gitignore_items()

        # Return True only if rel_path matches an exclude pattern AND does NOT
        # match an include pattern. Else, return False
        if (self._match_excl_regexp(rel_path) and
                not self._match_incl_regexp(rel_path)):

            return True

        return False

    def on_modified(self, event):
        """
        """

        rel_path = os.path.relpath(event.src_path, self.project_path)
        if rel_path == '.gitignore':
            # Reparse the gitignore.
            self._populate_gitignore_items()

        super(EventHandlerGit, self).on_modified(event)

    def _populate_gitignore_items(self):
        """ This method populates include and exclude lists with
        compiled regexps objects.
        """

        # Reset the include_regexps and exclude_regexps.
        self.include_regexps = []
        self.exclude_regexps = [re.compile('.*\.git/.*\.lock'),
                                re.compile('.*\.baboon-timestamp'),
                                re.compile('.*baboon.*')]

        # If there's a .gitignore file in the watched directory.
        if os.path.exists(self.gitignore_path):
            # Parse the gitignore.
            ignores = self._parse_gitignore()
            if ignores is not None:
                # Populate the regexps list with the ignores result.
                self.include_regexps += [re.compile(x) for x in ignores[0]]
                self.exclude_regexps += [re.compile(x) for x in ignores[1]]

    def _match_excl_regexp(self, rel_path):
        """ Returns True if rel_path matches any item in
        exclude_regexp list.
        """

        for regexp in self.exclude_regexps:
            if regexp.search(rel_path) is not None:
                self.logger.debug("The path %s matches the ignore regexp"
                                  " %s." % (rel_path, regexp.pattern))
                return True

        return False

    def _match_incl_regexp(self, rel_path):
        """ Returns True if rel_path matches any item in
        include_regexp list.
        """

        for neg_regexp in self.include_regexps:
            if neg_regexp.search(rel_path) is not None:
                self.logger.debug("The same path %s matches the include"
                                  " regexp %s." % (rel_path,
                                                   neg_regexp.pattern))
                return True

        return False

    def _parse_gitignore(self):
        """ Parses the .gitignore file in the repository.
        Returns a tuple with:
        1st elem: negative regexps (regexps to not match)
        2nd elem: regexps
        """
        gitignore_path = os.path.join(self.project_path, '.gitignore')
        lines = []  # contains each line of the .gitignore file
        results = []  # contains the result regexp patterns
        neg_results = []  # contains the result negative regexp patterns

        try:
            with open(gitignore_path, 'r') as f:
                lines = f.readlines()
        except IOError as err:
            raise BaboonException(format(err))

        # Sort the line in order to have inverse pattern first
        lines = sorted(lines, key=cmp_to_key(self._gitline_comparator))

        # For each git pattern, convert it to regexp pattern
        for line in lines:
            regexp = self._gitline_to_regexp(line)
            if regexp is not None:
                if not line.startswith('!'):
                    results.append(regexp)
                else:
                    neg_results.append(regexp)

        return neg_results, results

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
            line = line[1:]
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

        if not negation:
            regex = '.*%s.*' % regex

        return regex
