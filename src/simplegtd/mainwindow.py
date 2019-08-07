import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gtk

import simplegtd.rememberingwindow
import simplegtd.filterlist
import simplegtd.views


def shorten_path(filename):
    if filename.startswith(os.path.expanduser("~/")):
        filename = "~/" + filename[len(os.path.expanduser("~/")):]
    return filename


class SimpleGTDMainWindow(Gtk.ApplicationWindow, simplegtd.rememberingwindow.RememberingWindow):

    __gsignals__ = {
        'open-file-activated': (GObject.SIGNAL_RUN_LAST, None, ()),
        'new-window-activated': (GObject.SIGNAL_RUN_LAST, None, ()),
        'exit-activated': (GObject.SIGNAL_RUN_LAST, None, ()),
    }
    # FIXME: implement new window combo with Ctrl+N.
    # FIXME: implement quit and request with Ctrl+Q.
    # https://developer.gnome.org/gtk3/stable/gtk3-Bindings.html

    def __init__(self, todotxt, window_state_file):
        Gtk.ApplicationWindow.__init__(self)
        self.set_default_size(800, 600)
        simplegtd.rememberingwindow.RememberingWindow.__init__(self, window_state_file)
        self.set_title('Simple GTD')

        choosefile_button = Gtk.Button.new_from_icon_name("document-open", Gtk.IconSize.LARGE_TOOLBAR)
        choosefile_button.connect("clicked", lambda _: self.emit("open-file-activated"))

        new_view_button = Gtk.Button.new_from_icon_name("window-new", Gtk.IconSize.LARGE_TOOLBAR)
        new_view_button.connect("clicked", lambda _: self.emit("new-window-activated"))

        exit_button = Gtk.Button.new_from_icon_name("application-exit", Gtk.IconSize.LARGE_TOOLBAR)
        exit_button.connect("clicked", lambda _: self.emit("exit-activated"))

        header_bar = Gtk.HeaderBar()
        header_bar.set_property('expand', False)
        header_bar.set_title('Tasks')
        header_bar.set_subtitle(shorten_path(todotxt.name() or "(no file)"))
        header_bar.set_show_close_button(True)
        header_bar.pack_end(exit_button)
        header_bar.pack_end(new_view_button)
        header_bar.pack_end(choosefile_button)

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
