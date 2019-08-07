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
