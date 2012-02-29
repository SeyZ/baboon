import os

from errors.baboon_exception import BaboonException
from config import Config
from diff_match_patch import diff_match_patch


class Diffman(object):
    def __init__(self):
        self.config = Config()
        self.differ = diff_match_patch()

        # configures the level severity (0 = very strict, 1 = relax)
        self.differ.Match_Threshold = 0.05

    def diff(self, a, b):
        """ Creates a patch between oldfile and newfile
        """
        with open(a, 'r') as old:
            with open(b, 'r') as new:
                oldtext = old.read()
                newtext = new.read()

                thepatch = self.differ.patch_make(oldtext, newtext)
                patch_stringified = self.differ.patch_toText(thepatch)

                return patch_stringified

    def patch(self, patch, thefile, content=None):
        thepatch = patch
        if isinstance(patch, str):
            thepatch = self.differ.patch_fromText(patch)

        result = None
        try:
            filename = os.path.join(self.config.path, thefile)
            with open(filename, 'r') as f:
                content = f.read()
                result = self.differ.patch_apply(thepatch, content)
        except OSError as err:
            raise BaboonException(err)

        return result
