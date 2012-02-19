import jsonpickle
from diff_match_patch import diff_match_patch


class Diffman(object):
    def __init__(self):
        self.differ = diff_match_patch()

    def diff(self, a, b):
        with open(a, 'r') as old:
            with open(b, 'r') as new:
                oldtext = old.read()
                newtext = new.read()

                thepatch = self.differ.patch_make(oldtext, newtext)
                pickled = jsonpickle.encode(thepatch)

                return pickled


diffman = Diffman()
