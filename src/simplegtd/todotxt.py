#!/usr/bin/python3

import logging

import gi
gi.require_version('Gdk', '3.0')
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk

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

    blobstore = None
    linestore = None
    taskstore = None

    def __init__(self):
        Gtk.ListStore.__init__(self, object, str)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.blobstore = simplegtd.models.blobstore.FileBlobStore()
        self.linestore = simplegtd.models.linestore.LineStore(self.blobstore)
        self.taskstore = simplegtd.models.taskstore.TaskStore(self.linestore)
        simplegtd.models.liststoresyncer.ListStoreSyncer.__init__(
            self, self, self.taskstore,
            lambda r: [r[0]], lambda r: [r[0], markup_for(r[0].text)],
        )

    def name(self):
        return self.blobstore.name

    def open(self, filename):
        return self.blobstore.open(filename)

    def close(self):
        simplegtd.models.liststoresyncer.ListStoreSyncer.close(self)
        self.taskstore.close()
        self.linestore.close()
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
        self.linestore._save()
