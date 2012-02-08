import os

from config import config


class Initializor(object):
    def __init__(self):
        if not config.path:
            print "No path specified."
            return

        metadir = "%s%s" % (config.path, '.baboon')

        if not os.path.exists(metadir):
            os.mkdir(metadir)
            print 'done.'
