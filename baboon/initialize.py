import os

from config import config


class Initializor(object):
    def __init__(self):
        metadir = os.path.join(config.path, ".baboon")

        # Create the metadata folder if it doesn't exist
        if not os.path.exists(metadir):
            os.mkdir(metadir)
            print 'done.'
        else:
            print "This folder has already been initialized."
