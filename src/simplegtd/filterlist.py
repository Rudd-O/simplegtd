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
        self.tokens_contained_in_row = []
        self.token_visible = collections.defaultdict(bool)
        self.append(["All tasks", "", "", "All tasks"])
        todotxt.connect("row-inserted", self.todotxt_row_inserted_or_changed)
        todotxt.connect("row-changed", self.todotxt_row_inserted_or_changed)
        todotxt.connect("row-deleted", self.todotxt_row_deleted)
        for n, unused_row in enumerate(todotxt):
            self.todotxt_row_inserted_or_changed(todotxt, Gtk.TreePath.new_from_indices([n]), None)

    def todotxt_row_inserted_or_changed(self, todotxt, path, unused_it):
        row = path.get_indices()[0]
        text = todotxt[path][0].text

        # Fill up the list to capacity.
        while len(self.tokens_contained_in_row) <= row:
            self.tokens_contained_in_row.append([])
        # Remember the old tokens before the change.
        old_tokens = self.tokens_contained_in_row[row]
        # Zero out the token store for this row.
        self.tokens_contained_in_row[row] = []

        # The task is empty?  Do nothing then.
        if text is None:
            # Deref old tokens, return.
            self._deref_old_tokens(old_tokens, [])
            return
        else:
            # Deref old tokens ignoring new ones.
            new_tokens = [t.strip() for t in text.split()]
            self._deref_old_tokens(old_tokens, new_tokens)

        # Add tokens that are not visible at the moment.
        for tok in new_tokens:
            if tok.startswith("@") or tok.startswith("+"):
                self.tokens_contained_in_row[row].append(tok)
                if not self.token_visible[tok]:
                    sortable = ("1" if tok.startswith("@") else "2") + tok
                    self.append([tok, sortable, tok, markup_for(tok)])
                    self.token_visible[tok] = True

    def todotxt_row_deleted(self, unused_todotxt, path):
        row = path.get_indices()[0]
        old_tokens = self.tokens_contained_in_row[row]
        # Remove the tokens on the way out.
        self.tokens_contained_in_row.pop(row)
        # Deref old tokens.
        self._deref_old_tokens(old_tokens, [])

    def _deref_old_tokens(self, old_tokens, new_tokens):
        # Compute tokens of remaining tasks, then remove filter
        # elements that do not correspond to tokens of remaining tasks.
        remaining = set(tok for rowtoks in self.tokens_contained_in_row for tok in rowtoks)
        remaining = remaining | set(new_tokens if new_tokens else [])
        for tok in old_tokens:
            if self.token_visible[tok] and tok not in remaining:
                self.token_visible[tok] = False
                for r in self:
                    if r[0] == tok:
                        self.remove(r.iter)
                        break

    def get_sorted(self):
        '''Wrap the FilterList into a sortable list.'''
        sorted_filters = Gtk.TreeModelSort(model=self)
        sorted_filters.set_sort_column_id(1, Gtk.SortType.ASCENDING)
        return sorted_filters

    def get_filter_string(self, iter_):
        '''Return the filter string pointed to by iter_.'''
        return self.get_value(iter_, 2)
