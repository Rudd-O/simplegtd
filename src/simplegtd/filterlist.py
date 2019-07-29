#!/usr/bin/python3

import collections
import logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

from simplegtd.task import markup_for


class FilterList(Gtk.ListStore):

    def __init__(self, todotxt):
        Gtk.ListStore.__init__(self, str, str, str, str)
        '''Contains filters to be applied to the task list.

        Columns:
           1. plain text string
           2. sortable representation
           3. filter string
           4. markup to render instead of plain text string
        '''
        self.logger = logging.getLogger(self.__class__.__name__)
        self.rows_that_contain_token = collections.defaultdict(list)
        self.tokens_contained_in_row = collections.defaultdict(list)
        self.token_iter_in_filter = {}
        self.append(["All tasks", "", "", "All tasks"])
        todotxt.connect("row-changed", self.todotxt_row_changed)
        todotxt.connect("row-deleted", self.todotxt_row_deleted)
        todotxt.connect("row-inserted", self.todotxt_row_inserted)
        for n, unused_row in enumerate(todotxt):
            self.todotxt_row_inserted(todotxt, Gtk.TreePath.new_from_indices([n]), None)

    def todotxt_row_inserted(self, todotxt, path, unused_it):
        row = path.get_indices()[0]
        text = todotxt[path][0]
        tokens = text.split()
        for tok in tokens:
            tok = tok.strip()
            if tok.startswith("@") or tok.startswith("+"):
                if row not in self.rows_that_contain_token[tok]:
                    self.rows_that_contain_token[tok].append(row)
                if tok not in self.tokens_contained_in_row[row]:
                    self.tokens_contained_in_row[row].append(tok)
                self.logger.debug("New ref count for %s: %s", tok, len(self.rows_that_contain_token[tok]))
                if tok not in self.token_iter_in_filter:
                    sortable = ("1" if tok.startswith("@") else "2") + tok
                    self.token_iter_in_filter[tok] = self.append([tok, sortable, tok, markup_for(tok)])

    def todotxt_row_deleted(self, unused_todotxt, path):
        row = path.get_indices()[0]
        for tok in self.tokens_contained_in_row[row]:
            self.rows_that_contain_token[tok].remove(row)
            self.logger.debug("New ref count for %s: %s", tok, len(self.rows_that_contain_token[tok]))
            if not self.rows_that_contain_token[tok]:
                it = self.token_iter_in_filter[tok]
                self.remove(it)
                del self.token_iter_in_filter[tok]
        del self.tokens_contained_in_row[row]

    def todotxt_row_changed(self, todotxt, path, it):
        self.todotxt_row_deleted(todotxt, path)
        self.todotxt_row_inserted(todotxt, path, it)

    def get_sorted(self):
        '''Wrap the FilterList into a sortable list.'''
        sorted_filters = Gtk.TreeModelSort(model=self)
        sorted_filters.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        return sorted_filters

    def get_filter_string(self, iter_):
        '''Return the filter string pointed to by iter_.'''
        return self.get_value(iter_, 2)
