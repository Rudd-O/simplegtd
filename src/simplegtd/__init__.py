#!/usr/bin/python3

__version__ = "0.0.1"


import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gdk, Gtk

import xdg.BaseDirectory


class WindowState(object):

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


class SmartApplicationWindow(Gtk.ApplicationWindow):

    def __init__(self, state_file):
        self.__state_file = state_file
        self.__window_state = WindowState.from_keyfile(self.__state_file)
        Gtk.ApplicationWindow.__init__(self)
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
        Gtk.ApplicationWindow.size_allocate(self, allocation)
        if (not (self.__window_state.is_maximized or self.__window_state.is_fullscreen)):
            s = self.get_size()
            self.__window_state.current_width = s.width
            self.__window_state.current_height = s.height

    def on_window_state_event(self, unused_window, window_state):
        self.__window_state.is_maximized = (window_state.new_window_state & Gdk.WindowState.MAXIMIZED) != 0
        self.__window_state.is_fullscreen = (window_state.new_window_state & Gdk.WindowState.FULLSCREEN) != 0

    def on_destroy(self, unused_window):
        self.__window_state.to_keyfile(self.__state_file)


class SimpleGTDMainWindow(SmartApplicationWindow):
    def __init__(self, state_file):
        SmartApplicationWindow.__init__(self, state_file)


class SimpleGTD(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self)
        self.config_dir = os.path.join(xdg.BaseDirectory.xdg_config_home, "simplegtd")
        if not os.path.isdir(self.config_dir):
            os.makedirs(self.config_dir)
        self.connect("activate", self.on_activate)
        self.connect("window-removed", self.main_window_removed)

    def on_activate(self, unused_ref):
        window = SimpleGTDMainWindow(os.path.join(self.config_dir, "window-state"))
        self.add_window(window)
        window.connect("destroy", lambda *a: self.remove_window(window))
        window.show()

    def main_window_removed(self, unused_ref, window):
        self.quit()

    def quit(self):
        Gtk.main_quit()


def main():
    app = SimpleGTD()
    GObject.idle_add(app.run)
    Gtk.main()
