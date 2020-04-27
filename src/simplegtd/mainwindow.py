import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
gi.require_version('Handy', '0.0')
from gi.repository import GObject, GLib, Gdk, Gtk, Handy

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


class FilterHeaderBar(Gtk.HeaderBar):

    saved_filter_text = ""
    text_filter_mode_active = False

    __gsignals__ = {
        'search-changed': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, (str,)),
        'search-deactivated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'activate': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
    }

    def __init__(self):
        Gtk.HeaderBar.__init__(self)
        self.set_show_close_button(False)
        self.set_title("Filters")
        self.text_filter_entry = Gtk.SearchEntry()
        self.text_filter_entry.set_placeholder_text("Search...")
        self.text_filter_entry.set_no_show_all(True)
        self.pack_start(self.text_filter_entry)
        self.search_button = Gtk.Button.new_from_icon_name("edit-find", Gtk.IconSize.LARGE_TOOLBAR)
        self.search_button.connect("clicked", lambda *_: self.activate_text_filter_mode())
        self.pack_start(self.search_button)
        self.text_filter_entry.connect("search-changed", lambda _: self.emit("search-changed", self.text_filter_entry.get_text()))
        self.text_filter_entry.connect("activate", lambda _: self.emit("activate"))
        self.text_filter_entry.connect("stop-search", lambda *_: self.deactivate_text_filter_mode())
        self.text_filter_entry.connect("focus-out-event", lambda *_: self.filter_unfocused())

    def filter_unfocused(self):
        if self.text_filter_mode_active:
            if self.text_filter_entry.is_visible() and not self.text_filter_entry.get_text().strip():
                self.deactivate_text_filter_mode()

    def activate_text_filter_mode(self):
        if not self.text_filter_mode_active:
            w = Gtk.Label()
            w.set_visible(False)
            self.set_custom_title(w)
            self.search_button.hide()
            self.text_filter_entry.set_text(self.saved_filter_text)
            self.text_filter_entry.show()
        self.text_filter_entry.grab_focus()
        self.text_filter_mode_active = True

    def deactivate_text_filter_mode(self):
        if self.text_filter_mode_active:
            self.text_filter_mode_active = False
            self.set_custom_title(None)
            self.saved_filter_text = self.text_filter_entry.get_text()
            self.text_filter_entry.set_text("")
            self.text_filter_entry.hide()
            self.search_button.show()
            self.emit("search-deactivated")

    def toggle_text_filter_mode(self):
        if self.text_filter_mode_active:
            if self.text_filter_entry.is_focus():
                self.deactivate_text_filter_mode()
            else:
                self.text_filter_entry.grab_focus()
        else:
            self.activate_text_filter_mode()


class SimpleGTDMainWindow(Gtk.ApplicationWindow, simplegtd.libwhiz.rememberingwindow.RememberingWindow):

    __gsignals__ = {
        'open-file-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'new-window-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'close-window-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'text-filter-toggled': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'exit-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
        'help-activated': (GObject.SIGNAL_RUN_LAST | GObject.SIGNAL_ACTION, None, ()),
    }

    filter_header_bar = FilterHeaderBar
    tasks_header_bar = Gtk.HeaderBar

    def __init__(self, todotxt, window_state_file):
        self.selection_filters = []
        self.search_filters = []

        Gtk.ApplicationWindow.__init__(self)
        self.set_default_icon_name("simplegtd")

        self.set_default_size(800, 600)
        simplegtd.libwhiz.rememberingwindow.RememberingWindow.__init__(self, window_state_file)

        accel_group = Gtk.AccelGroup()
        self.add_accel_group(accel_group)

        self.add_accelerator("close-window-activated", accel_group, ord('w'), Gdk.ModifierType.CONTROL_MASK, 0)
        self.connect("close-window-activated", lambda _: self.destroy())

        self.filter_header_bar = FilterHeaderBar()
        self.filter_header_bar.connect("search-changed", lambda _, text: self.filter_text_changed(text))
        self.filter_header_bar.connect("search-deactivated", lambda unused_entry: self.task_view.grab_focus())
        self.filter_header_bar.connect("activate", lambda unused_entry: self.task_view.grab_focus())
        self.add_accelerator("text-filter-toggled", accel_group, ord('f'), Gdk.ModifierType.CONTROL_MASK, 0)
        self.connect('text-filter-toggled', lambda *_: self.filter_header_bar.toggle_text_filter_mode())

        self.tasks_header_bar = Gtk.HeaderBar()
        self.tasks_header_bar.set_show_close_button(True)

        [x(make_title(todotxt)) for x in (self.tasks_header_bar.set_title, self.set_title)]
        todotxt.connect("row-inserted", self.recompute_subtitle)
        todotxt.connect("row-deleted", self.recompute_subtitle)
        self.recompute_subtitle(todotxt)

        exit_button = Gtk.Button.new_from_icon_name("application-exit", Gtk.IconSize.LARGE_TOOLBAR)
        exit_button.connect("clicked", lambda _: self.emit("exit-activated"))
        self.add_accelerator("exit-activated", accel_group, ord('q'), Gdk.ModifierType.CONTROL_MASK, 0)
        self.tasks_header_bar.pack_end(exit_button)

        new_view_button = Gtk.Button.new_from_icon_name("window-new", Gtk.IconSize.LARGE_TOOLBAR)
        new_view_button.connect("clicked", lambda _: self.emit("new-window-activated"))
        self.add_accelerator("new-window-activated", accel_group, ord('n'), Gdk.ModifierType.CONTROL_MASK, 0)
        self.tasks_header_bar.pack_end(new_view_button)

        choosefile_button = Gtk.Button.new_from_icon_name("document-open", Gtk.IconSize.LARGE_TOOLBAR)
        choosefile_button.connect("clicked", lambda _: self.emit("open-file-activated"))
        self.add_accelerator("open-file-activated", accel_group, ord('o'), Gdk.ModifierType.CONTROL_MASK, 0)
        self.tasks_header_bar.pack_end(choosefile_button)

        help_button = Gtk.Button.new_from_icon_name("system-help", Gtk.IconSize.LARGE_TOOLBAR)
        help_button.connect("clicked", lambda _: self.show_shortcuts_window())
        self.add_accelerator("help-activated", accel_group, Gdk.KEY_F1, 0, 0)
        self.connect("help-activated", lambda _: self.show_shortcuts_window())
        self.tasks_header_bar.pack_end(help_button)

        self.task_view = simplegtd.views.TaskView()
        todotxt.connect("ready", lambda *unused: self.task_view.focus_first())
        task_view_scroller = Gtk.ScrolledWindow()
        task_view_scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        task_view_scroller.add(self.task_view)

        self.filter_view = simplegtd.views.FilterView()
        GLib.idle_add(self.filter_view.select_first)
        self.filter_view.get_selection().connect("changed", self.filter_selection_changed)
        filter_view_scroller = Gtk.ScrolledWindow()
        filter_view_scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        filter_view_scroller.add(self.filter_view)

        filters = simplegtd.filterlist.FilterList(todotxt)
        self.task_view.set_model(todotxt)
        self.filter_view.set_model(filters)

        # Group the header bars.
        hg = Handy.HeaderGroup()
        hg.add_header_bar(self.filter_header_bar)
        hg.add_header_bar(self.tasks_header_bar)

        # Group the filter header bar and filter scroller list.
        sg = Gtk.SizeGroup()
        sg.set_mode(Gtk.SizeGroupMode.HORIZONTAL)
        sg.add_widget(self.filter_header_bar)
        sg.add_widget(filter_view_scroller)

        # Make the title bar.
        titlebox = Gtk.Box()
        titlebox.pack_start(self.filter_header_bar, False, True, 0)
        self.filter_header_bar.set_show_close_button(True)
        sep = Gtk.VSeparator()
        sep.get_style_context().add_class("sidebar")
        titlebox.add(sep)
        titlebox.pack_end(self.tasks_header_bar, True, True, 0)
        self.tasks_header_bar.set_show_close_button(True)
        ht = Handy.TitleBar()
        ht.add(titlebox)
        self.set_titlebar(ht)

        # Make the pane components and add the pane to the window.
        paned = Handy.Leaflet()
        paned.add(filter_view_scroller)
        paned.add(task_view_scroller)
        paned.set_visible_child(task_view_scroller)
        self.add(paned)

        self.task_view.grab_focus()

    def recompute_subtitle(self, model, *unused_args):
        # FIXME we need to show outstanding tasks rather than all tasks
        # (that requires a richer data model for the tasks stored in the
        # model) and we also require to show which ones are hidden by filters
        # as well as what filter is being used.  Perhaps a "last modified
        # n minutes ago" with a rough time would be useful.
        numtasks = len(model)
        self.tasks_header_bar.set_subtitle("%s tasks" % numtasks)

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
