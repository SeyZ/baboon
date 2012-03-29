import os

from base64 import b64decode
from zlib import decompress
from config import Config
from logger import logger


@logger
class Service(object):
    """ The purpose of the service is to manipulate payload of the
    Transport (from, to).
    """

    def __init__(self, diffman):
        self.config = Config()
        self.diffman = diffman

        # Key: author + filepath
        # Value: True if the last message received by the author was a
        # conflict
        self.in_conflict = {}

    def verify_msg(self, items):
        for item in items:
            try:
                payload = item['payload']
                filepath = payload[0].text
                thediff = payload[1].text
                thediff = b64decode(thediff)
                thediff = decompress(thediff)
                author = payload[2].text
            except IndexError:
                # If the payload is corrupted, continue in order to
                # process the next element (maybe it will be valid).
                self.logger.error("Received a corrupted payload")
                continue

            if author != self.config.jid:
                result = self.diffman.patch(thediff, "%s" % os.path.join(
                        self.config.path, filepath))
                if not result:
                    self.in_conflict[author + filepath] = True
                    msg = "Conflict detected with %s in %s" % \
                        (author, filepath)
                    self.logger.info(msg)
                    self.logger.debug("With the diff:\n%s" % thediff)
                    self.notify(msg)
                else:
                    if self.in_conflict.get(author + filepath):
                        msg = "Conflict resolved with %s in %s" % \
                            (author, filepath)
                        self.in_conflict[author + filepath] = False
                        self.logger.info(msg)
                        self.notify(msg)
                    else:
                        msg = "Everything seems to be perfect with" \
                            " %s in %s" % (author, filepath)
                        self.logger.debug(msg)
