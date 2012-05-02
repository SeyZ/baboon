import logging


def logger(cls):
    """ Adds a logger class attribute to the class 'cls'.
    By default, the logger is based on the name class.

    @param cls: the class will contains the new logger
    attribute
    """
    setattr(cls, 'logger',
            logging.getLogger('baboon.%s' % cls.__name__))
    return cls
