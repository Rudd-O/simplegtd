import hashlib
import os

import xdg.BaseDirectory


def find_data_file(filename, app, before=None):
    '''Searches for filename in os.path.join(datadir, app) for datadir
    in XDG_DATA_DIRS.  If before is not None, it looks for the file in that
    directory first.

    Raises:
        KeyError: if filename is not found.
    '''
    for path in (
        ([before] if before is not None else [])
        + [os.path.join(os.path.dirname(__file__), os.path.pardir, os.path.pardir, "data")]
        + [os.path.join(x, "simplegtd") for x in xdg.BaseDirectory.xdg_data_dirs]
    ):
        f = os.path.join(path, os.path.basename(filename))
        if os.path.isfile(f):
            return f
    raise KeyError(f)


def config_home(subdir=None):
    if subdir is None:
        return xdg.BaseDirectory.xdg_config_home
    return os.path.join(xdg.BaseDirectory.xdg_config_home, subdir)


def data_home(subdir=None):
    if subdir is None:
        return xdg.BaseDirectory.xdg_data_home
    return os.path.join(xdg.BaseDirectory.xdg_data_home, subdir)


def cache_home(subdir=None):
    if subdir is None:
        return xdg.BaseDirectory.xdg_cache_home
    return os.path.join(xdg.BaseDirectory.xdg_cache_home, subdir)


def strip_data_home(path):
    '''Given a path (relative or absolute), strips the beginning of the path
    if it begins with `data_home()`, else returns the same path unchanged.'''
    abspath = os.path.abspath(path)
    if abspath.startswith(data_home() + "/") or abspath == data_home():
        return abspath[len(data_home()) + 1:]
    return path


def abbrev_home(filename):
    '''Given a path (relative or absolute), changes the path to use ~/
    notation if it is within $HOME, else returns the same path unchanged.'''
    absfilename = os.path.abspath(filename)
    if absfilename.startswith(os.path.expanduser("~/")):
        return "~/" + absfilename[len(os.path.expanduser("~/")):]
    return filename


def hash_path(filename):
    '''Returns an MD5 sum of a file name path.  Or any string, really.'''
    h = hashlib.md5()
    h.update(filename.encode("utf-8", "ignore"))
    h = h.hexdigest()
    return h
