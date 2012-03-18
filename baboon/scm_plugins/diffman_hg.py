import os
import tempfile
import shutil

from diffman import Diffman
from hgapi import Repo


class DiffmanHg(Diffman):

    @property
    def scm_name(self):
        return 'hg'

    def diff(self, filepath):
        """ Computes the diff of the filepath
        """

        repo = Repo(self.config.path)
        thepatch = self._escape(repo.hg_command("diff"))

        return thepatch

    def patch(self, patch, thefile, content=None):
        # if there's no diff, there's no conflict
        if patch in ("", None):
            return True

        try:
            # write the file in a temporary file
            tmpfile = tempfile.mkstemp()
            os.write(tmpfile[0], patch)

            # create a temp directory
            tmpdir = tempfile.mkdtemp()
            tmprepo = Repo(tmpdir)

            # initialize a new hg repo
            tmprepo.hg_init()

            # copy the file to patch in the temp directory
            shutil.copy2(thefile, tmpdir)

            # add the file to the temp hg repo
            tmprepo.hg_add('.')

            # commit the current working tree
            tmprepo.hg_commit('Baboon commit')

            # import the patch in the tmpfile hg repo
            try:
                tmprepo.hg_command('import', tmpfile[1], '--no-commit')
            except:
                # an exception is raised if the command failed
                return False
        finally:
            try:
                os.remove(tmpfile[1])
                shutil.rmtree(tmpdir)
            except:
                """ There's at least one error during the clean of tmpfile files.
                it's a pity but not fatal."""
                pass

        return True
