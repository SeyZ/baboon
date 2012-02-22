from diff_match_patch import diff_match_patch


class Diffman(object):
    def __init__(self):
        self.differ = diff_match_patch()

        # configures the level severity (0 = very strict, 1 = relax)
        self.differ.Match_Threshold = 0.3

    def diff(self, a, b):
        with open(a, 'r') as old:
            with open(b, 'r') as new:
                oldtext = old.read()
                newtext = new.read()

                thepatch = self.differ.patch_make(oldtext, newtext)
                patch_stringified = self.differ.patch_toText(thepatch)

                return patch_stringified

    def patch(self, patch_stringified):
        thepatch = self.differ.patch_fromText(patch_stringified)
        print thepatch

diffman = Diffman()
