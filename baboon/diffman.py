import os

from errors.baboon_exception import BaboonException
from config import Config
from diff_match_patch import diff_match_patch


class Diffman(object):
    def __init__(self):
        self.config = Config()
        self.dmp = diff_match_patch()

        # configures the level severity (0 = very strict, 1 = relax)
        self.dmp.Match_Threshold = 0.03
        self.dmp.Match_DeleteThresold = 0.03
        self.dmp.Patch_Margin = 0

    def diff(self, a, b):
        """ Creates a patch between oldfile and newfile
        """
        if not os.path.exists(a):
            open(a, 'a').close()

        if not os.path.exists(b):
            open(b, 'a').close()

        with open(a, 'r') as old:
            with open(b, 'r') as new:
                oldtext = old.read()
                newtext = new.read()

                diffs = self._diff_lineMode(oldtext, newtext)
                thepatch = self.dmp.patch_make(diffs)
                patch_stringified = self.dmp.patch_toText(thepatch)

                return patch_stringified

    def patch(self, patch, thefile, content=None):
        thepatch = patch
        if isinstance(patch, str):
            thepatch = self.dmp.patch_fromText(patch)

        result = None
        try:
            filename = os.path.join(self.config.path, thefile)
            with open(filename, 'r') as f:
                content = f.read()
                result = self.dmp.patch_apply(thepatch, content)
        except OSError as err:
            raise BaboonException(err)

        return result

    def _diff_lineMode(self, text1, text2):
        a = self.dmp.diff_linesToChars(text1, text2)
        line_text1 = a[0]
        line_text2 = a[1]
        lines = a[2]

        diffs = self.dmp.diff_main(line_text1, line_text2, False)
        self.dmp.diff_charsToLines(diffs, lines)

        return diffs
