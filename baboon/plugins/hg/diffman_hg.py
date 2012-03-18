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
        thepatch = self._escape(repo.hg_command("diff", filepath))

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
            rel_path = os.path.relpath(thefile, self.config.path)
            self._dir_tree(rel_path, tmpdir)

            shutil.copy2(thefile, os.path.join(tmpdir, rel_path))

            # add the file to the temp hg repo
            tmprepo.hg_add('.')

            # commit the current working tree
            tmprepo.hg_commit('Baboon commit')

            # import the patch in the tmpfile hg repo
            try:
                tmprepo.hg_command('import', tmpfile[1], '--no-commit')
            except Exception:
                # an exception is raised if the command failed
                return False
        finally:
            try:
                os.remove(tmpfile[1])
                shutil.rmtree(tmpdir)
            except:
                """ There's at least one error during the clean of tmpfile
                files. It's a pity but not fatal."""
                pass

        return True

    def _dir_tree(self, rel_path, tmpdir):
        """ Create the same directory structure of rel_path to the tmpdir
        directory.
        """
        splitted = os.path.split(rel_path)
        aggr = []

        # Suppose the rel_path is equals to 'models/database/foo.js'.
        # aggr will be ['models', 'models/database', 'models/database/foo.js']
        for i, elem in enumerate(splitted):
            if i > 0:
                aggr.append(os.path.join(splitted[i - 1], splitted[i]))
            else:
                aggr.append(splitted[i])  # i == 0

        for cur in aggr:
            d = os.path.join(self.config.path, cur)
            if os.path.isdir(d):
                os.mkdir(os.path.join(tmpdir, cur))
            elif os.path.isfile(d):
                break
