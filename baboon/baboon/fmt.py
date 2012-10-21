from re import match
from getpass import getpass
from termcolor import colored, cprint
from baboon.common.errors.baboon_exception import CommandException


# Fix Python 2.x. input
try:
    input = raw_input
except:
    pass


def cerr(msg):
    """ Displays the formatted msg with an error style.
    """

    cprint(msg, 'red', attrs=['bold'])


def csuccess(msg):
    """ Displays the formatted msg with a success style.
    """

    cprint(msg, 'green', attrs=['bold'])


def cwarn(msg):
    """
    """

    cprint(msg, 'yellow', attrs=['bold'])


def cblabla(msg):
    """
    """

    cprint(msg, attrs=['bold'])


def cinput(prompt, validations=[], secret=False):
    """ Retrieves the user input with a formatted prompt. Return the value when
    the value entered by the user matches all validations. The validations is a
    list of tuple. The first element of the tuple is the regexp, the second is
    the error message when the input does not match the regexp.
    """

    # The future return value.
    ret = None

    # Iterate until input matches all validations.
    while True:
        valid = True

        # Get the user input and put it into ret.
        colored_prompt = colored(prompt, attrs=['bold'])
        ret = getpass(prompt=colored_prompt) if secret else \
            input(colored_prompt)

        # Iterates over validations...
        for validation, possible_err in validations:
            if not match(validation, ret):
                # The input is not valid. Print an error message and set the
                # valid flag to False to avoid to exit the while True loop.
                cerr(possible_err)
                valid = False

        # Exit the loop if the valid flag is True.
        if valid:
            break

    return ret


def cinput_yes_no(prompt):
    ret = input(colored(prompt + ' (y/n) ', attrs=['bold']))
    return ret.lower() in ('true', 'y', 'yes')


def confirm_cinput(prompt, validations=[], possible_err="", secret=False):

    ret = cinput(prompt, secret=secret)

    # Iterates over validations...
    for validation, err in validations:
        if not match(validation, ret):
            raise CommandException(500, err)

    confirm_ret = cinput('Confirm %s' % prompt.lower(), secret=secret)

    if ret == confirm_ret:
        return ret
    else:
        # The values are not the same.
        raise CommandException(500, possible_err)
