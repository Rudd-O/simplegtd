#!/usr/bin/python3

__version__ = "0.0.1"


import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gdk, Gtk, Gio

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
    def __init__(self, todotxt, window_state_file):
        SmartApplicationWindow.__init__(self, window_state_file)
        self.set_title('Simple GTD')
        header_bar = Gtk.HeaderBar()
        header_bar.set_property('expand', False)
        header_bar.set_title('Tasks')
        header_bar.set_show_close_button(True)
        self.set_titlebar(header_bar)
        view = Gtk.TreeView(todotxt)
        renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.connect("edited", lambda _, path, new_text: todotxt.task_edited(path, new_text))
        column = Gtk.TreeViewColumn("Task", renderer, text=0)
        view.append_column(column)
        self.add(view)


class TodoTxt(Gtk.ListStore):

    todofile = None
    last_line_cr = False
    entries = 0

    def __init__(self):
        Gtk.ListStore.__init__(self, str)

    def disestablish_handler(self):
        self.monitor_dir.disconnect(self.monitor_handle)

    def establish_handler(self):
        self.monitor_handle = self.monitor_dir.connect("changed", self.dir_changed)

    @classmethod
    def from_file(klass, filename):
        self = klass()
        self.todofile = filename
        self.giofile_dir = Gio.File.new_for_path(os.path.dirname(self.todofile))
        self.monitor_dir = self.giofile_dir.monitor(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.establish_handler()
        self.load()
        return self

    def dir_changed(self, monitor, f, newf, event):
        if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.load()
        elif event == Gio.FileMonitorEvent.RENAMED:
            if newf.get_basename() == os.path.basename(self.todofile):
                self.load()

    def task_edited(self, path, new_text):
        if self[path][0] == new_text:
            return
        self.set_value(self[path].iter, 0, new_text)
        self.save()

    def load(self):
        if not self.todofile:
            return
        entries = 0
        try:
            with open(self.todofile, "r") as f:
                lines = f.readlines()
                self.last_line_cr = lines and lines[-1] and lines[-1][-1] == "\n"
                for n, line in enumerate(lines):
                    if line and line[-1] == "\n":
                        line = line[:-1]
                    entries += 1
                    try:
                        if self[n][0] != line:
                            self.set_value(self[n].iter, 0, line)
                    except IndexError:
                        self.append([line])
        except FileNotFoundError:
            pass
        while self.entries > entries:
            self.remove(self[-1].iter)
            self.entries -= 1
        self.entries = entries
        return self

    def save(self):
        '''Saves the todo tasks list.'''
        if not self.todofile:
            return
        lines = [row[0] + "\n" for row in self]
        if not self.last_line_cr:
            if lines:
                lines[-1] = lines[-1][:-1]
        text = "".join(lines)
        try:
            with open(self.todofile, "r") as f:
                if text == f.read():
                    return
        except FileNotFoundError:
            pass

        self.disestablish_handler()
        with open(self.todofile, "w") as f:
            f.write(text)
            f.flush()
        GObject.idle_add(self.establish_handler)


class SimpleGTD(Gtk.Application):

    def __init__(self):
        Gtk.Application.__init__(self)
        self.config_dir = os.path.join(xdg.BaseDirectory.xdg_config_home, "simplegtd")
        self.data_dir = os.path.join(xdg.BaseDirectory.xdg_data_home, "simplegtd")
        for d in self.config_dir, self.data_dir:
            if not os.path.isdir(d):
                os.makedirs(d)
        self.connect("activate", self.on_activate)
        self.connect("window-removed", self.main_window_removed)

    def on_activate(self, unused_ref):
        try:
            self.model = TodoTxt.from_file(os.path.join(self.data_dir, "todo.txt"))
            window = SimpleGTDMainWindow(self.model, os.path.join(self.config_dir, "window-state"))
            self.add_window(window)
            window.connect("destroy", lambda *a: self.remove_window(window))
            window.show_all()
        except BaseException:
            Gtk.main_quit()
            raise

    def main_window_removed(self, unused_ref, window):
        self.quit()

    def quit(self):
        Gtk.main_quit()


def main():
    app = SimpleGTD()
    GObject.idle_add(app.run)
    Gtk.main()
