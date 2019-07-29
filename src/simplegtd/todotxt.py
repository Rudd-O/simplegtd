#!/usr/bin/python3

import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gio


class TodoTxt(Gtk.ListStore):

    todofile = None
    last_line_cr = False
    entries = 0

    def __init__(self):
        Gtk.ListStore.__init__(self, str)

    def __disestablish_handler(self):
        self.monitor_dir.disconnect(self.monitor_handle)

    def __establish_handler(self):
        self.monitor_handle = self.monitor_dir.connect("changed", self.dir_changed)

    def dir_changed(self, unused_monitor, unused_f, newf, event):
        if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.__load()
        elif event == Gio.FileMonitorEvent.RENAMED:
            if newf.get_basename() == os.path.basename(self.todofile):
                self.__load()

    @classmethod
    def from_file(klass, filename):
        self = klass()
        self.todofile = filename
        self.giofile_dir = Gio.File.new_for_path(os.path.dirname(self.todofile))
        self.monitor_dir = self.giofile_dir.monitor(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.__establish_handler()
        self.__load()
        return self

    def close(self):
        if not self.todofile:
            return
        self.__disestablish_handler()
        self.monitor_dir.cancel()

    def edit(self, path, new_text):
        if self[path][0] == new_text:
            return
        self.set_value(self[path].iter, 0, new_text)
        self.__save()

    def __load(self):
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

    def __save(self):
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

        self.__disestablish_handler()
        with open(self.todofile, "w") as f:
            f.write(text)
            f.flush()
        GLib.idle_add(self.__establish_handler)
