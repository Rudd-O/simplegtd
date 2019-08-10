#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gdk


def get_base_attr(klass, attr):
    '''Retrieves a class attribute from one of the bases of self.

    Arguments:
        klass: The class you want to get the class base attribute from.

    Returns:
        The class attribute in question, or None if not found.
    '''
    for base_ in klass.__bases__:
        if base_ == klass:
            continue
        if not hasattr(base_, attr):
            continue
        return getattr(base_, attr)


class _WindowState(object):

    current_width = None
    current_height = None
    is_maximized = None
    is_fullscreen = None

    @classmethod
    def from_keyfile(klass, filename):
        self = klass()
        f = GLib.KeyFile.new()
        try:
            f.load_from_file(filename, GLib.KeyFileFlags.NONE)
            self.current_width = f.get_integer("window_state", "current_width")
            self.current_height = f.get_integer("window_state", "current_height")
            self.is_maximized = f.get_boolean("window_state", "is_maximized")
            self.is_fullscreen = f.get_boolean("window_state", "is_fullscreen")
        except GLib.Error:
            pass
        return self

    def to_keyfile(self, filename):
        '''Saves the window state to a keyfile.

        The directory containing the filename must already exist.
        '''
        f = GLib.KeyFile.new()
        try:
            f.load_from_file(filename, GLib.KeyFileFlags.NONE)
        except GLib.Error:
            pass
        if self.current_width is not None:
            f.set_integer("window_state", "current_width", self.current_width)
        if self.current_height is not None:
            f.set_integer("window_state", "current_height", self.current_height)
        if self.is_maximized is not None:
            f.set_boolean("window_state", "is_maximized", self.is_maximized)
        if self.is_fullscreen is not None:
            f.set_boolean("window_state", "is_fullscreen", self.is_fullscreen)
        f.save_to_file(filename)


class RememberingWindow(object):
    '''Mixin class for Gtk.Window and Gtk.ApplicationWindow that remembers
    its onscreen position, given a state file to store this info.

    Derived (perhaps imperfectly) from:
    https://wiki.gnome.org/HowDoI/SaveWindowState
    '''

    def __init__(self, state_file):
        '''Initializes the RememberingWindow object.

        Takes a path name where the window state will be saved.
        Per XDG standards, we recommend a file inside the folder
        `simplegtd.libwhiz.path.cache_home(yourappname)`.

        If you call self.set_default_size() after initializing
        this object, this object will not work as advertised. In other
        words: please invoke self.__init__(state_file) after initializing
        the Gtk.Window / Gtk.ApplicationWindow you're mixing this class
        into, and also after any calls to self.set_default_size().
        '''
        if not get_base_attr(self.__class__, "size_allocate"):
            raise TypeError(
                "%s must subclass a Gtk.Window or subclass thereof" % (
                    self
                )
            )

        self.__state_file = state_file
        self.__window_state = _WindowState.from_keyfile(self.__state_file)
        if (self.__window_state.current_width is not None
            and self.__window_state.current_height is not None):
            self.set_default_size(self.__window_state.current_width,
                                  self.__window_state.current_height)
        if self.__window_state.is_maximized:
            self.maximize()
        if self.__window_state.is_fullscreen:
            self.fullscreen()
        self.connect('size-allocate', self.on_size_allocate)
        self.connect('window-state-event', self.on_window_state_event)
        self.connect("destroy", self.on_destroy)

    def on_size_allocate(self, unused_window, allocation):
        size_allocate = get_base_attr(self.__class__, "size_allocate")
        size_allocate(self, allocation)
            
        if (not (self.__window_state.is_maximized or self.__window_state.is_fullscreen)):
            s = self.get_size()
            self.__window_state.current_width = s.width
            self.__window_state.current_height = s.height

    def on_window_state_event(self, unused_window, window_state):
        self.__window_state.is_maximized = (window_state.new_window_state & Gdk.WindowState.MAXIMIZED) != 0
        self.__window_state.is_fullscreen = (window_state.new_window_state & Gdk.WindowState.FULLSCREEN) != 0

    def on_destroy(self, unused_window):
        self.__window_state.to_keyfile(self.__state_file)
