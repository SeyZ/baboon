from git import Repo
from config import Config


class Diffman(object):
    def __init__(self):
        self.config = Config()

    def diff(self, filepath):
        """ Computes the diff of the filepath
        """
        repo = Repo(self.config.path)
        hcommit = repo.commit('master')
        diffs = hcommit.diff(None, paths=filepath, create_patch=True)

        thepatch = ''
        for i in diffs:
            thepatch += i.diff

        thepatch = self._escape(thepatch)

        return thepatch

    def patch(self, patch, thefile, content=None):
        repo = Repo(self.config.path)

        with open('/tmp/patchfile', 'w') as f:
            f.write(patch)

        git = repo.git
        try:
            output = git.apply('--check', '/tmp/patchfile')
        except:
            return False

        return output == ""

    def _escape(self, text):
        escaped_text = map(lambda x: "<![CDATA[%s]]>" % x, text.split("]]>"))
        return "<![CDATA[]]]><![CDATA[]>]]>".join(escaped_text)
