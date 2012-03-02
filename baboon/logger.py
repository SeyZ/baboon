import logging


def logger(theclass):
    """ Adds a logger instance attribute to the class 'theclass'.
    By default, the logger is based on the name class.

    @param theclass: the instance of theclass will contains the new logger
    attribute
    """
    def new(cls, *args, **kwargs):
        result = super(cls, cls).__new__(cls)
        setattr(result, 'logger',
                logging.getLogger('baboon.%s' % cls.__name__))
        return result

    theclass.__new__ = staticmethod(new)
    return theclass
