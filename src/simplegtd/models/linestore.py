#!/usr/bin/python3

import difflib
import logging

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk


# FIXME it's probably prudent to create a Mapper between the LineStore
# and the filesystem, so that I can move the hairy load/save code
# outside of this, and then the interface between the file system
# and the LineStore is just lines, no more than that.
# Perhaps it becomes even possible to consolidate the TaskStore and
# the ListStore completely.  Fundamentally the concern of handling the
# file system stuff and the one of handling the actual in-memory repr
# of the line/task store should not be mixed in one single class.
class LineStore(Gtk.ListStore):

    last_line_cr = False
    __watches = None

    __gsignals__ = {
        'unserialized': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'serialized': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self):
        Gtk.ListStore.__init__(self, str)
        self.logger = logging.getLogger(self.__class__.__name__)

    def unserialize(self, unused_bs, text, exc):
        self.logger.debug("Load begun.  Lines: %s.", len(text.splitlines()))
        if exc is not None:
            # Oops.  The blobstore had a problem.
            # Our caller deals with these situations.  We do not know how.
            return

        new_lines = text.splitlines(True)
        existing_lines = [t[0] for t in self]
        self.last_line_cr = new_lines and new_lines[-1] and new_lines[-1][-1] == "\n"
        def strip_cr(line):
            if line and line[-1] == "\n":
                line = line[:-1]
            return line
        new_lines = [strip_cr(l) for l in new_lines]
        if new_lines and not new_lines[-1]:
            new_lines = new_lines[:-1]

        diff = difflib.SequenceMatcher()
        diff.set_seqs(existing_lines, new_lines)
        added = 0
        removed = 0
        changed = 0
        for op, i1, i2, j1, j2 in diff.get_opcodes():
            if op == 'equal':
                pass
            elif op == 'insert':
                r = 0
                for row in new_lines[j1:j2]:
                    #self.logger.debug("Inserting row %s", i1 + r)
                    self.insert(i1 + r, row=[row])
                    r = r + 1
                    added += 1
            elif op == 'delete':
                for r in reversed(range(i1, i2)):
                    #self.logger.debug("Removing row %s", r)
                    self.remove(self[r].iter)
                    removed += 1
            elif op == 'replace':
                if i2 - i1 == j2 - j1:
                    # The number of rows replaced is the same in old and new.
                    for r in range(i2 - i1):
                        #self.logger.debug("Replacing row %s with new row %s", i1 + 1, j1 + r)
                        self.set_value(self[i1 + r].iter, 0, new_lines[j1 + r])
                        changed += 1
                elif i2 - i1 > j2 - j1:
                    # The number of rows replaced is larger in old than in new.
                    for r in reversed(range((i2 - i1) - (j2 - j1))):
                        #self.logger.debug("Removing row %s", i1 + r)
                        self.remove(self[i1+r].iter)
                        removed += 1
                    for r in range(j2 - j1):
                        #self.logger.debug("Replacing row %s with new row %s", i1 + 1, j1 + r)
                        self.set_value(self[i1 + r].iter, 0, new_lines[j1 + r])
                        changed += 1
                else: # i2 - i1 < j2 - j1:
                    # The number of rows replaced is larger in new than in old.
                    for r in range((j2 - j1) - (i2 - i1)):
                        #self.logger.debug("Inserting row %s  %r", i1 + r, new_lines[j1 + r])
                        self.insert(i1 + r, [new_lines[j1 + r]])
                        added += 1
                    for r in range(j2 - j1):
                        #self.logger.debug("Replacing row %s with new row %s  %r", i1 + 1, j1 + r, new_lines[j1 + r])
                        self.set_value(self[i1 + r].iter, 0, new_lines[j1 + r])
                        changed += 1
            else:
                assert 0, "not reached: %s" % op
        self.logger.debug("Load finished.  %s additions, %s removals, %s changes.  Lines: %s.", added, removed, changed, len(self))
        self.emit('unserialized')

    def serialize(self):
        lines = [row[0] + "\n" for row in self]
        if not self.last_line_cr:
            if lines:
                lines[-1] = lines[-1][:-1]
        text = "".join(lines)
        self.emit('serialized')
        return text
