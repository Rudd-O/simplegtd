import os

import xdg.BaseDirectory


def find_data_file(filename):
    '''Raises KeyError if filename is not found in XDG_DATA_DIRS.'''
    for path in (
        [os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, "data")]
        + [os.path.join(x, "simplegtd") for x in xdg.BaseDirectory.xdg_data_dirs]
    ):
        f = os.path.join(path, os.path.basename(filename))
        if os.path.isfile(f):
            return f
    raise KeyError(f)


def config_dir():
    return os.path.join(xdg.BaseDirectory.xdg_config_home, "simplegtd")


def data_home():
    return os.path.join(xdg.BaseDirectory.xdg_data_home, "simplegtd")


def strip_data_home(path):
    if path.startswith(data_home() + "/") or path == data_home():
        return path[len(data_home()) + 1:]
    return path


def shorten_path(filename):
    if filename.startswith(os.path.expanduser("~/")):
        filename = "~/" + filename[len(os.path.expanduser("~/")):]
    return filename
