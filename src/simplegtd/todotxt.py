#!/usr/bin/python3

import difflib
import logging
import os

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, Gtk, Gio

from simplegtd.task import markup_for


class TodoTxt(Gtk.ListStore):

    todofile = None
    last_line_cr = False

    def __init__(self):
        Gtk.ListStore.__init__(self, str, str)
        self.logger = logging.getLogger(self.__class__.__name__)

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

    def name(self):
        return self.todofile

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

    def remove_at(self, iter_):
        Gtk.ListStore.remove(self, iter_)
        self.__save()

    def new_at(self, iter_):
        if iter_ is not None:
            path = self.get_path(iter_)
            row = path[0]
        else:
            row = 0
        new_iter = Gtk.ListStore.insert(self, row, ["", ""])
        return new_iter

    def get_at(self, iter_):
        return self.get_value(iter_, 0)

    def remove_many(self, iters):
        for iter_ in iters:
            Gtk.ListStore.remove(self, iter_)
        self.__save()

    def edit(self, iter_, new_text):
        '''Edit task at iter_.  Does nothing if the line does not change.'''
        if self.get_value(iter_, 0) == new_text:
            return
        self.set_value(iter_, 0, new_text)
        self.set_value(iter_, 1, markup_for(new_text))
        self.__save()

    def _load_from_lines(self, new_lines):
        existing_lines = [t[0] for t in self]
        self.last_line_cr = new_lines and new_lines[-1] and new_lines[-1][-1] == "\n"
        def strip_cr(line):
            if line and line[-1] == "\n":
                line = line[:-1]
            return line
        new_lines = [strip_cr(l) for l in new_lines]
        diff = difflib.SequenceMatcher()
        diff.set_seqs(existing_lines, new_lines)
        for op, i1, i2, j1, j2 in diff.get_opcodes():
            if op == 'equal':
                pass
            elif op == 'insert':
                r = 0
                for row in new_lines[j1:j2]:
                    self.logger.debug("Inserting row %s", i1 + r)
                    self.insert(i1 + r, row=[row, markup_for(row)])
                    r = r + 1
            elif op == 'delete':
                for r in reversed(range(i1, i2)):
                    self.logger.debug("Removing row %s", r)
                    self.remove(self[r].iter)
            elif op == 'replace':
                if i2 - i1 == j2 - j1:
                    # The number of rows replaced is the same in old and new.
                    for r in range(i2 - i1):
                        self.logger.debug("Replacing row %s with new row %s", i1 + 1, j1 + r)
                        self.set_value(self[i1 + r].iter, 0, new_lines[j1 + r])
                        self.set_value(self[i1 + r].iter, 1, markup_for(new_lines[j1 + r]))
                elif i2 - i1 > j2 - j1:
                    # The number of rows replaced is larger in old than in new.
                    for r in reversed(range((i2 - i1) - (j2 - j1))):
                        self.logger.debug("Removing row %s", i1 + r)
                        self.remove(self[i1+r].iter)
                    for r in range(j2 - j1):
                        self.logger.debug("Replacing row %s with new row %s", i1 + 1, j1 + r)
                        self.set_value(self[i1 + r].iter, 0, new_lines[j1 + r])
                        self.set_value(self[i1 + r].iter, 1, markup_for(new_lines[j1 + r]))
                else: # i2 - i1 < j2 - j1:
                    # The number of rows replaced is larger in new than in old.
                    for r in range((j2 - j1) - (i2 - i1)):
                        self.logger.debug("Inserting row %s", i1 + r)
                        self.insert(i1 + r)
                    for r in range(j2 - j1):
                        self.logger.debug("Replacing row %s with new row %s", i1 + 1, j1 + r)
                        self.set_value(self[i1 + r].iter, 0, new_lines[j1 + r])
                        self.set_value(self[i1 + r].iter, 1, markup_for(new_lines[j1 + r]))
            else:
                assert 0, "not reached: %s" % op
        return

    def __load(self):
        if not self.todofile:
            return
        try:
            with open(self.todofile, "r") as f:
                lines = f.readlines()
                self._load_from_lines(lines)
        except FileNotFoundError:
            pass
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
