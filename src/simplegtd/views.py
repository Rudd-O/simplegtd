import gi
gi.require_version('Pango', '1.0')
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Pango, Gdk, Gtk

import simplegtd.libwhiz.css


class TaskView(Gtk.TreeView):

    filters = None
    filter_displays_empty_tasks = False
    editing_iter = None

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.set_headers_visible(False)
        self.set_property('expand', True)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.cell = renderer = Gtk.CellRendererText()
        renderer.set_property('editable', True)
        renderer.set_property('wrap-mode', Pango.WrapMode.WORD)
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        renderer.connect("edited", self.task_edited)
        renderer.connect("editing-canceled", self.task_editing_canceled)
        self.column = Gtk.TreeViewColumn("Task", renderer, markup=1)
        self.append_column(self.column)
        self.connect("key-press-event", self.key_press_event)

    def key_press_event(self, unused_widget, event):
        # FIXME if modifier keys are depressed these should probably be ignored.
        if event.keyval in (Gdk.KEY_Delete, Gdk.KEY_KP_Delete):
            filtered_model, selected_paths = self.get_selection().get_selected_rows()
            underlying_model = filtered_model.get_model()
            to_remove = []
            for path in reversed(selected_paths):
                filtered_iter = filtered_model[path].iter
                underlying_iter = filtered_model.convert_iter_to_child_iter(filtered_iter)
                to_remove.append(underlying_iter)
            underlying_model.remove_many(to_remove)
        elif event.keyval in (Gdk.KEY_Insert, Gdk.KEY_KP_Insert, Gdk.KEY_plus):
            self.filter_displays_empty_tasks = True
            self.get_model().refilter()
            # FIXME: implement Shift+Insert to do the same as Ctrl+V
            filtered_model, selected_paths = self.get_selection().get_selected_rows()
            underlying_model = filtered_model.get_model()
            pos = None
            for path in selected_paths:
                filtered_iter = filtered_model[path].iter
                pos = filtered_model.convert_iter_to_child_iter(filtered_iter)
                break
            new_row_iter = underlying_model.new_at(pos)
            self.editing_iter = new_row_iter
            got_set, new_filtered_row_iter = filtered_model.convert_child_iter_to_iter(new_row_iter)
            if got_set:
                self.get_selection().unselect_all()
                self.get_selection().select_iter(new_filtered_row_iter)
                self.scroll_to_cell(filtered_model.get_path(new_filtered_row_iter), self.column)
                self.set_cursor(filtered_model.get_path(new_filtered_row_iter), self.column, True)

    def task_editing_canceled(self, unused_renderer):
        if self.editing_iter:
            if self.get_model().get_model().get_at(self.editing_iter) == "":
                self.get_model().get_model().remove_at(self.editing_iter)
        self.editing_iter = None

    def task_edited(self, unused_renderer, path, new_text):
        filtered_model = self.get_model()
        todotxt_model = filtered_model.get_model()
        filtered_iter = filtered_model[path].iter
        todotxt_iter = filtered_model.convert_iter_to_child_iter(filtered_iter)
        if new_text == "":
            todotxt_model.remove_at(todotxt_iter)
        else:
            todotxt_model.edit(todotxt_iter, new_text)
        self.filter_displays_empty_tasks = False
        self.get_model().refilter()

    def set_model(self, model):
        Gtk.TreeView.set_model(self, model.filter_new())

    def filter_func(self, model, it, unused_ptr):
        task = model.get_value(it, 0).text
        if self.filter_displays_empty_tasks and task == "":
            return True
        pluses = []
        ats = []
        substrings = []
        for flt in self.filters:
            if flt == "":
                continue
            elif flt.startswith("+"):
                pluses.append(flt.lower())
            elif flt.startswith("@"):
                ats.append(flt.lower())
            else:
                substrings.append(flt.lower())
        has_any_pluses = any(i in task.lower() for i in pluses) if pluses else True
        has_any_ats = any(i in task.lower() for i in ats) if ats else True
        has_all_substrings = all(i in task.lower() for i in substrings) if substrings else True
        result = has_any_pluses and has_any_ats and has_all_substrings
        return result

    def set_filters(self, filters):
        if self.filters is None:
            self.filters = filters
            self.get_model().set_visible_func(self.filter_func)
        else:
            self.filters = filters
            self.get_model().refilter()

    def focus_first(self):
        try:
            model = self.get_model()
            self.set_cursor_on_cell(
                model.get_path(model[0].iter),
                self.column,
                self.cell,
                False
            )
        except IndexError: pass


class FilterView(Gtk.TreeView):

    css = """
.filter_view {
    background-color: transparent;
    color: @theme_text_color;
}
.filter_view:selected {
    color: @theme_selected_fg_color;
    background-color: @theme_selected_bg_color;
}
"""

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.set_headers_visible(False)
        self.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        renderer = Gtk.CellRendererText()
        renderer.ellipsize = Pango.EllipsizeMode.MIDDLE
        c = Gtk.TreeViewColumn("Filters", renderer, markup=3)
        c.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        self.append_column(c)
        simplegtd.libwhiz.css.add(self.css)
        self.get_style_context().add_class("filter_view")

    def set_model(self, model):
        Gtk.TreeView.set_model(self, model.get_sorted())

    def get_filters_from_selection(self, tree_selection):
        filter_strings = []
        sorted_model, paths = tree_selection.get_selected_rows()
        underlying_model = sorted_model.get_model()
        for path in paths:
            sorted_iter = sorted_model[path].iter
            underlying_iter = sorted_model.convert_iter_to_child_iter(sorted_iter)
            filter_strings.append(underlying_model.get_filter_string(underlying_iter))
        return filter_strings

    def select_first(self):
        try:
            model = self.get_model()
            self.get_selection().select_iter(model[0].iter)
        except IndexError: pass
