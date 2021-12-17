import sys

__verbose__: bool = False


def _getVerbose():
    """
    Returns True if verbose printing is active
    """
    global __verbose__

    return __verbose__ or sys.flags.debug


def printVerbose(*args):
    """
    Print verbose message

    TODO: This print can then optionally be redirected to log file or something..
    """
    if _getVerbose():
        print(*args)


def setVerbose(verbose=True):
    """
    Verbosity is used to print extra information about the processing of commands.

    :param verbose: If True, turn on verbose printing to stdout
    """
    global __verbose__

    __verbose__ = verbose
