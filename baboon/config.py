import os


def singleton(cls):
    instances = {}
    def getinstance():
        if cls not in instances:
            instances[cls] = cls()
        return instances[cls]
    return getinstance

@singleton
class Config(object):
    def __init(self):
        self.path = ""

    def check_config(self):
        return os.path.isdir("%s%s" % (self.path, '.baboon'))

config = Config()
