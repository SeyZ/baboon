import os


class Config(object):
    def __init__(self):
        self.path = os.path.abspath(".")

    def check_config(self):
        return os.path.isdir(os.path.join(self.path, ".baboon"))

config = Config()
