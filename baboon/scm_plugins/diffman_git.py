import os
import tempfile

from  diffman import Diffman
from git import Repo
from config import Config


class DiffmanGit(Diffman):
    def __init__(self):
        self.config = Config()

    @property
    def scm_name(self):
        return 'git'

    def diff(self, filepath):
        """ Computes the diff of the filepath
        """
        repo = Repo(self.config.path)
        hcommit = repo.commit('HEAD')
        diffs = hcommit.diff(None, paths=filepath, create_patch=True)

        thepatch = ''
        for i in diffs:
            thepatch += i.diff

        thepatch = self._escape(thepatch)

        return thepatch

    def patch(self, patch, thefile, content=None):
        # if there's no diff, there's no conflict
        if patch in ("", None):
            return True

        # open the scm repository
        repo = Repo(self.config.path)

        # write the file in a temporary file
        tmp = tempfile.mkstemp()
        os.write(tmp[0], patch)

        git = repo.git
        try:
            output = git.apply('--check', tmp[1])
        except:
            return False

        return output == ""

    def _escape(self, text):
        escaped_text = map(lambda x: "<![CDATA[%s]]>" % x, text.split("]]>"))
        return "<![CDATA[]]]><![CDATA[]>]]>".join(escaped_text)
