#!/usr/bin/python3

__version__ = "0.0.3"


import collections
import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gdk, Gtk, Gio

import xdg.BaseDirectory

import simplegtd.filterlist
import simplegtd.rememberingwindow
import simplegtd.todotxt
import simplegtd.views


class SimpleGTDMainWindow(Gtk.ApplicationWindow, simplegtd.rememberingwindow.RememberingWindow):

    def __init__(self, todotxt, window_state_file):
        Gtk.ApplicationWindow.__init__(self)
        simplegtd.rememberingwindow.RememberingWindow.__init__(self, window_state_file)
        self.set_title('Simple GTD')
        self.set_default_size(800, 600)

        header_bar = Gtk.HeaderBar()
        header_bar.set_property('expand', False)
        header_bar.set_title('Tasks')
        header_bar.set_show_close_button(True)
        self.set_titlebar(header_bar)

        self.task_view = simplegtd.views.TaskView()
        task_view_scroller = Gtk.ScrolledWindow()
        task_view_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        task_view_scroller.add(self.task_view)

        self.filter_view = simplegtd.views.FilterView()
        self.filter_view.get_selection().connect("changed", self.filter_selection_changed)
        filter_view_scroller = Gtk.ScrolledWindow()
        filter_view_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        filter_view_scroller.add(self.filter_view)

        filters = simplegtd.filterlist.FilterList(todotxt)
        self.task_view.set_model(todotxt)
        self.filter_view.set_model(filters)

        GLib.idle_add(self.task_view.focus_first)
        GLib.idle_add(self.filter_view.select_first)

        paned = Gtk.Paned()
        paned.set_wide_handle(True)
        paned.pack1(filter_view_scroller, False, False)
        paned.add2(task_view_scroller)

        self.add(paned)
        self.task_view.grab_focus()

    def filter_selection_changed(self, tree_selection):
        filter_strings = self.filter_view.get_filters_from_selection(tree_selection)
        self.task_view.set_filters(filter_strings)


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
            self.model = simplegtd.todotxt.TodoTxt.from_file(os.path.join(self.data_dir, "todo.txt"))
            window = SimpleGTDMainWindow(self.model, os.path.join(self.config_dir, "window-state"))
            self.add_window(window)
            window.connect("destroy", lambda *unused_a: self.remove_window(window))
            window.show_all()
        except BaseException:
            Gtk.main_quit()
            raise

    def main_window_removed(self, unused_ref, unused_window):
        self.model.close()
        self.quit()

    def quit(self):
        Gtk.main_quit()


def main():
    app = SimpleGTD()
    GLib.idle_add(app.run)
    Gtk.main()


if __name__ == "__main__":
    # FIXME remove debug code.
    main()
