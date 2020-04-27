#!/usr/bin/python3

import logging

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GObject, Gtk

import simplegtd.models.blobstore
import simplegtd.models.linestore
import simplegtd.models.taskstore
import simplegtd.models.liststoresyncer
from simplegtd.task import markup_for


# FIXME: using some pygtk magic, eliminate the need for this additional sync
# between the taskstore and the todotxt (effectively eliminating this one
# object for good, or paring it down to a stub), by using cellrenderers
# that use markup generated directly from the Task object, because only the
# task object knows how to adequately identify the tokens present in the task
# text.
class TodoTxt(Gtk.ListStore, simplegtd.models.liststoresyncer.ListStoreSyncer):

    filename = None
    blobstore = None
    linestore = None
    taskstore = None

    __gsignals__ = {
        'ready': (GObject.SIGNAL_RUN_FIRST, None, ()),
    }

    def __init__(self, filename):
        Gtk.ListStore.__init__(self, object, str)
        self.filename = filename
        self.logger = logging.getLogger(self.__class__.__name__)
        self.blobstore = simplegtd.models.blobstore.FileBlobStore()
        self.linestore = simplegtd.models.linestore.LineStore()
        self.__watches = [
            self.blobstore.connect("done-reading", self.linestore.unserialize),
        ]
        self.__ready_watches = [
            self.linestore.connect("unserialized", self.__on_first_unserialize),
        ]
        self.taskstore = simplegtd.models.taskstore.TaskStore(self.linestore)
        simplegtd.models.liststoresyncer.ListStoreSyncer.__init__(
            self, self, self.taskstore,
            lambda r: [r[0]], lambda r: [r[0], markup_for(r[0].text)],
        )

    def __on_first_unserialize(self, *unused):
        # Only fires the first time that the linestore is unserialized.
        self.linestore.disconnect(self.__ready_watches[-1])
        self.__ready_watches = self.__ready_watches[:-1]
        self.logger.debug("Successful unserialize of the linestore.  Emitting ready().")
        self.emit('ready')

    def name(self):
        return self.filename

    def open(self):
        return self.blobstore.open(self.filename)

    def close(self):
        simplegtd.models.liststoresyncer.ListStoreSyncer.close(self)
        self.taskstore.close()
        [self.linestore.disconnect(w) for w in self.__ready_watches]
        [self.blobstore.disconnect(w) for w in self.__watches]
        self.blobstore.close()

    def remove_at(self, iter_):
        Gtk.ListStore.remove(self, iter_)
        self.__save()

    def new_at(self, iter_):
        if iter_ is not None:
            path = self.get_path(iter_)
            row = path[0]
        else:
            row = 0
        new_iter = Gtk.ListStore.insert(self, row, [simplegtd.models.taskstore.Task.fromstring(""), ""])
        return new_iter

    def get_at(self, iter_):
        return self.get_value(iter_, 0).text

    def remove_many(self, iters):
        removed = False
        for iter_ in iters:
            removed = True
            Gtk.ListStore.remove(self, iter_)
        if removed:
            self.__save()

    def edit(self, iter_, new_text):
        '''Edit task at iter_.  Does nothing if the line does not change.'''
        if self.get_value(iter_, 0).text == new_text:
            return
        self[iter_][0].set_text(new_text)
        self[iter_][1] = markup_for(new_text)
        self.__save()

    def __save(self):
        '''Saves the todo tasks list.'''
        text = self.linestore.serialize()
        # FIXME errors in puts must be handled somehow.
        # Right now they are not handled.
        self.blobstore.put(text)
