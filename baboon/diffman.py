import os
import subprocess
import shlex

from errors.baboon_exception import BaboonException
from config import Config


class Diffman(object):
    def __init__(self):
        self.config = Config()

    def diff(self, a, b):
        """ Creates a patch between oldfile and newfile
        """
        if not os.path.exists(a):
            open(a, 'a').close()

        if not os.path.exists(b):
            open(b, 'a').close()

        cmd = 'diff %s %s' % (a, b)
        args = shlex.split(cmd)
        result = subprocess.Popen(args, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE)
        output, error = result.communicate()
        thepatch = self._escape(output)

        return thepatch

    def patch(self, patch, thefile, content=None):
        m = '/tmp/patchfile'

        with open(m, 'w') as f:
            f.write(patch)
            f.flush()

        cmd = 'patch -s %s -i %s -o /tmp/resultpatch' % (thefile, m)
        args = shlex.split(cmd)
        p = subprocess.Popen(args, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE)
        output, error = p.communicate()

        return output == "" and error == ""

    def _escape(self, text):
        escaped_text = map(lambda x: "<![CDATA[%s]]>" % x, text.split("]]>"))
        return "<![CDATA[]]]><![CDATA[]>]]>".join(escaped_text)
