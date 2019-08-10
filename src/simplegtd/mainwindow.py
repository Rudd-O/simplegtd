import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, GLib, Gdk, Gtk

import simplegtd.libwhiz.rememberingwindow
import simplegtd.filterlist
import simplegtd.libwhiz.path
import simplegtd.views


def make_title(todotxt):
    if todotxt.name():
        n = todotxt.name()
        bn = os.path.basename(n)
        dn = simplegtd.libwhiz.path.strip_data_home(os.path.dirname(n))
        if dn:
            dn = simplegtd.libwhiz.path.abbrev_home(dn)
            title = "%s (%s)" % (bn, dn)
        else:
            title = "%s" % bn
        return title
    return 'Simple GTD (in memory)'


class SimpleGTDMainWindow(Gtk.ApplicationWindow, simplegtd.libwhiz.rememberingwindow.RememberingWindow):

    __gsignals__ = {
        'open-file-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'new-window-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'close-window-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'exit-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'help-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'text-filter-focus-request': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
    }

    header_bar = Gtk.HeaderBar

    def __init__(self, todotxt, window_state_file):
        self.selection_filters = []
        self.search_filters = []

        Gtk.ApplicationWindow.__init__(self)
        self.set_default_size(800, 600)
        simplegtd.libwhiz.rememberingwindow.RememberingWindow.__init__(self, window_state_file)

        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        self.add_accelerator("close-window-activated", accel_group, ord('w'), Gdk.ModifierType.CONTROL_MASK, 0)
        self.connect("close-window-activated", lambda _: self.destroy())

        header_bar = Gtk.HeaderBar()
        self.header_bar = header_bar
        header_bar.set_property('expand', False)
        header_bar.set_show_close_button(True)

        [x(make_title(todotxt)) for x in (header_bar.set_title, self.set_title)]
        self.set_titlebar(header_bar)
        todotxt.connect("row-inserted", self.recompute_subtitle)
        todotxt.connect("row-deleted", self.recompute_subtitle)
        self.recompute_subtitle(todotxt)

        text_filter_entry = Gtk.SearchEntry()
        text_filter_entry.set_placeholder_text("Search tasks...")
        text_filter_entry.connect("search-changed", lambda entry: self.filter_text_changed(entry.get_text()))
        text_filter_entry.connect("stop-search", lambda entry: entry.set_text("") or self.task_view.grab_focus())
        text_filter_entry.connect("activate", lambda unused_entry: self.task_view.grab_focus())
        self.add_accelerator("text-filter-focus-request", accel_group, ord('f'), Gdk.ModifierType.CONTROL_MASK, 0)
        self.connect("text-filter-focus-request", lambda _: text_filter_entry.grab_focus())
        header_bar.pack_start(text_filter_entry)

        exit_button = Gtk.Button.new_from_icon_name("application-exit", Gtk.IconSize.LARGE_TOOLBAR)
        exit_button.connect("clicked", lambda _: self.emit("exit-activated"))
        self.add_accelerator("exit-activated", accel_group, ord('q'), Gdk.ModifierType.CONTROL_MASK, 0)
        header_bar.pack_end(exit_button)

        new_view_button = Gtk.Button.new_from_icon_name("window-new", Gtk.IconSize.LARGE_TOOLBAR)
        new_view_button.connect("clicked", lambda _: self.emit("new-window-activated"))
        self.add_accelerator("new-window-activated", accel_group, ord('n'), Gdk.ModifierType.CONTROL_MASK, 0)
        header_bar.pack_end(new_view_button)

        choosefile_button = Gtk.Button.new_from_icon_name("document-open", Gtk.IconSize.LARGE_TOOLBAR)
        choosefile_button.connect("clicked", lambda _: self.emit("open-file-activated"))
        self.add_accelerator("open-file-activated", accel_group, ord('o'), Gdk.ModifierType.CONTROL_MASK, 0)
        header_bar.pack_end(choosefile_button)

        help_button = Gtk.Button.new_from_icon_name("system-help", Gtk.IconSize.LARGE_TOOLBAR)
        help_button.connect("clicked", lambda _: self.show_shortcuts_window())
        self.add_accelerator("help-activated", accel_group, Gdk.KEY_F1, 0, 0)
        self.connect("help-activated", lambda _: self.show_shortcuts_window())
        header_bar.pack_end(help_button)

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

    def recompute_subtitle(self, model, *unused_args):
        # FIXME we need to show outstanding tasks rather than all tasks
        # (that requires a richer data model for the tasks stored in the
        # model) and we also require to show which ones are hidden by filters
        # as well as what filter is being used.  Perhaps a "last modified
        # n minutes ago" with a rough time would be useful.
        numtasks = len(model)
        self.header_bar.set_subtitle("%s tasks" % numtasks)

    def filter_selection_changed(self, tree_selection):
        filter_strings = self.filter_view.get_filters_from_selection(tree_selection)
        self.selection_filters = filter_strings
        self.task_view.set_filters(self.selection_filters + self.search_filters)

    def filter_text_changed(self, new_text):
        filter_strings = []
        if new_text.strip():
            filter_strings.append(new_text.strip())
        self.search_filters = filter_strings
        self.task_view.set_filters(self.selection_filters + self.search_filters)

    def show_shortcuts_window(self):
        builder = Gtk.Builder()
        d, j = os.path.dirname, os.path.join
        builder.add_from_file(
            simplegtd.libwhiz.path.find_data_file(
                "shortcuts-window.ui",
                "simplegtd",
                before=j(d(d(d(__file__))), "data")
            )
        )
        shortcuts_window = builder.get_object("shortcuts-simplegtd")
        shortcuts_window.set_transient_for(self)
        shortcuts_window.show_all()
        shortcuts_window.set_property("view-name", "")
        shortcuts_window.set_property("section-name", "shortcuts")
