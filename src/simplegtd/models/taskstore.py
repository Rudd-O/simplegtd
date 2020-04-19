import collections
import datetime
import logging
import re

import gi
gi.require_version('GObject', '2.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk

import simplegtd.models.liststoresyncer

RegexCapsule = collections.namedtuple('RegexCapsule', 'regex group')


CREATION_DATE_RE = RegexCapsule(re.compile(r'(^|\s)(\d\d\d\d-[0-1]\d-[0-3]\d)($|\s)'), 2)
THRESHOLD_DATE_RE = RegexCapsule(re.compile(r'(^|\s)t:(\d\d\d\d-[0-1]\d-[0-3]\d)($|\s)'), 2)


def unencap(capsule, text):
    try:
        r = capsule.regex.search(text)
    except TypeError:
        print(repr(text))
        raise
    if r is None:
        return None
    return r.group(capsule.group)


# FIXME: TODO: add unit tests for this stuff
# FIXME: finish task parsing, based on Simpletask task formatting.
class Task(GObject.GObject):

    __gsignals__ = {
        'changed': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    creation_date = None
    threshold_date = None
    text = ""

    def __init__(self):
        GObject.GObject.__init__(self)

    def __str__(self):
        return '<%s>' % self.text

    def __repr__(self):
        return self.__str__()

    @classmethod
    def fromstring(klass, text):
        k = klass()
        k.text = text
        k._update()
        return k

    def set_text(self, new_text):
        if new_text != self.text:
            self.text = new_text
            self._update()
            self.emit("changed")

    def _update(self):
        self._update_creation_date()
        self._update_threshold_date()

    def _unencap(self, capsule):
        return unencap(capsule, self.text)

    def _update_creation_date(self):
        ds = self._unencap(CREATION_DATE_RE)
        if ds:
            try:
                self.creation_date = datetime.datetime.strptime(ds, "%Y-%m-%d").date()
            except ValueError:
                self.creation_date = None
        else:
            self.creation_date = None

    def _update_threshold_date(self):
        ds = self._unencap(THRESHOLD_DATE_RE)
        if ds:
            try:
                self.threshold_date = datetime.datetime.strptime(ds, "%Y-%m-%d").date()
            except ValueError:
                self.threshold_date = None
        else:
            self.threshold_date = None


class TaskStore(Gtk.ListStore, simplegtd.models.liststoresyncer.ListStoreSyncer):

    linestore = None

    def __init__(self, linestore):
        Gtk.ListStore.__init__(self, object)
        simplegtd.models.liststoresyncer.ListStoreSyncer.__init__(
            self, self, linestore,
            lambda r: [r[0].text], lambda r: [Task.fromstring(r[0])],
        )
        self.logger = logging.getLogger(self.__class__.__name__)
        self.linestore = linestore

    def on_task_changed(self, task):
        iter_ = self.get_iter_first()
        while iter_:
            if self[iter_][0] is task:
                break
            iter_ = self.iter_next(iter_)
        if iter_:
            self.emit("row-changed", self.get_path(iter_), iter_)

    def on_row_changed(self, source, path, iter_, *unused):
        if source == self:
            return simplegtd.models.liststoresyncer.ListStoreSyncer.on_row_changed(
                self, source, path, iter_, *unused
            )
        text = source[path][0]
        task = self[path][0]
        if text != task.text:
            self.handler_block(self.watches[self][0])
            task.set_text(text)
            self.handler_unblock(self.watches[self][0])

    def on_row_deleted(self, source, path, *unused):
        if source == self.linestore:
            task = self[path][0]
            task.disconnect_by_func(self.on_task_changed)
        return simplegtd.models.liststoresyncer.ListStoreSyncer.on_row_deleted(
            self, source, path, *unused
        )

    def on_row_inserted(self, source, path, *unused):
        ret = simplegtd.models.liststoresyncer.ListStoreSyncer.on_row_inserted(
            self, source, path, *unused
        )
        self[path][0].connect("changed", self.on_task_changed)
        return ret

    def close(self):
        simplegtd.models.liststoresyncer.ListStoreSyncer.close(self)
        for row in self:
            row[0].disconnect_by_func(self.on_task_changed)
