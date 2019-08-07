#!/usr/bin/python3

__version__ = "0.0.7"


import collections
import hashlib
import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gdk, Gtk, Gio

import xdg.BaseDirectory

import simplegtd.todotxt
import simplegtd.mainwindow


def hash_path(filename):
    h = hashlib.md5()
    h.update(filename.encode("utf-8", "ignore"))
    h = h.hexdigest()
    return h


class _SimpleGTDAppState(object):

    todo_txts = None
    __app_state_file = None

    def __init__(self, filename):
        self.__app_state_file = filename
        f = GLib.KeyFile.new()
        try:
            f.load_from_file(filename, GLib.KeyFileFlags.NONE)
            self.todo_txts = f.get_string_list("general", "todo_txts")
        except GLib.Error:
            pass
        return self

    def persist_app_state(self):
        f = GLib.KeyFile.new()
        try:
            f.load_from_file(self.__app_state_file, GLib.KeyFileFlags.NONE)
        except GLib.Error:
            pass
        if self.todo_txts is not None:
            f.set_string_list("general", "todo_txts", self.todo_txts)
        f.save_to_file(self.__app_state_file)


class SimpleGTD(Gtk.Application, _SimpleGTDAppState):

    def __init__(self):
        Gtk.Application.__init__(self)
        self.config_dir = os.path.join(xdg.BaseDirectory.xdg_config_home, "simplegtd")
        self.data_dir = os.path.join(xdg.BaseDirectory.xdg_data_home, "simplegtd")
        for d in self.config_dir, self.data_dir:
            if not os.path.isdir(d):
                os.makedirs(d)

        settings_file = os.path.join(self.config_dir, "app-settings")
        _SimpleGTDAppState.__init__(self, settings_file)
        self.default_todo_txt = os.path.join(self.data_dir, "todo.txt")
        if not self.todo_txts:
            self.todo_txts = [self.default_todo_txt]

        self.connect("activate", lambda _: [self.add_new_todo_window(x) for x in self.todo_txts] and None)
        self.connect("window-removed", self.todo_window_removed)
        self.models_to_windows = {}

    def delegate_open_file_activated(self, requestor):
        choosefile_dialog = Gtk.FileChooserDialog(
            title="Select an existing TODO.TXT file or create a new one",
            parent=requestor,
            action=Gtk.FileChooserAction.SAVE,
            buttons=(
                Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OPEN, Gtk.ResponseType.OK,
                "Use default", Gtk.ResponseType.NONE,
            )
        )
        response = choosefile_dialog.run()
        choosefile_dialog.hide()
        if response == Gtk.ResponseType.OK:
            self.add_new_todo_window(choosefile_dialog.get_filename())
        elif response == Gtk.ResponseType.NONE:
            self.add_new_todo_window(self.default_todo_txt)
        choosefile_dialog.destroy()

    def delegate_new_window_activated(self, requestor):
        for data_file, (unused_model, windows) in self.models_to_windows.items():
            if requestor in windows:
                self.add_new_todo_window(data_file)

    def delegate_exit_activated(self, unused_requestor):
        self.quit()

    def add_new_todo_window(self, data_file):
        try:
            if data_file in self.models_to_windows:
                model = self.models_to_windows[data_file][0]
            else:
                model = simplegtd.todotxt.TodoTxt.from_file(data_file)
            window = simplegtd.mainwindow.SimpleGTDMainWindow(model, os.path.join(self.config_dir, "window-state-" + hash_path(data_file)))
            self.add_window(window)
            if data_file not in self.models_to_windows:
                self.models_to_windows[data_file] = (model, [])
            self.models_to_windows[data_file][1].append(window)
            window.connect("open-file-activated", self.delegate_open_file_activated)
            window.connect("new-window-activated", self.delegate_new_window_activated)
            window.connect("exit-activated", self.delegate_exit_activated)
            window.connect("destroy", self.remove_window)
            window.show_all()
        except BaseException:
            Gtk.main_quit()
            raise

    def todo_window_removed(self, unused_ref, window):
        for data_file, (model, windows) in list(self.models_to_windows.items()):
            if window in windows:
                windows.remove(window)
            if not windows:
                model.close()
                del self.models_to_windows[data_file]
        if not self.models_to_windows:
            self.quit()
        else:
            self.todo_txts = list(self.models_to_windows.keys())
            self.persist_app_state()

    def quit(self):
        if self.models_to_windows:
            # First, we disconnect our own todo_window_removed handler,
            # since while quitting we do not want that handler to handle
            # whittling down the window list.
            self.disconnect_by_func(self.todo_window_removed)
            # Now we persist everything.
            self.todo_txts = list(self.models_to_windows.keys())
            self.persist_app_state()
            for model, windows in list(self.models_to_windows.values()):
                for window in windows:
                    window.destroy()
            for model, windows in list(self.models_to_windows.values()):
                model.close()
        Gtk.main_quit()


def main():
    app = SimpleGTD()
    GLib.idle_add(app.run)
    Gtk.main()


if __name__ == "__main__":
    main()
