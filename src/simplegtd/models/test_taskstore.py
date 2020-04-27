import datetime
import unittest

import gi
gi.require_version('GLib', '2.0')
from gi.repository import GLib

import simplegtd.models.taskstore as ts
import simplegtd.models.linestore as ls
import simplegtd.models.blobstore as bs


class TaskStoreTest(unittest.TestCase):

    def setUp(self):
        self.b = bs.StringBlobStore()
        self.l = ls.LineStore()
        self.b.connect("done-reading", self.l.unserialize)
        self.t = ts.TaskStore(self.l)
        self.c = GLib.MainContext.default()

    def run_loop(self):
        while self.c.pending():
            self.c.iteration(False)

    def tearDown(self):
        del self.c
        self.t.close()
        del self.t
        self.b.disconnect_by_func(self.l.unserialize)
        del self.l
        self.b.close()
        del self.b

    def test_adding_to_blobstore_adds_tasks(self):
        text = "abc 2020-04-03 a task t:2020-05-05"
        self.b.open(text)
        self.run_loop()
        assert len(self.t) == 1
        task = self.t[0][0]
        self.assertEqual(text, task.text)
        self.assertEqual(task.creation_date, datetime.date(2020, 4, 3))
        self.assertEqual(task.threshold_date, datetime.date(2020, 5, 5))

        text2 = "cdef"
        text = text2 + "\n" + text
        # Simulate write to backend, and its side effect.
        self.b.put(text)
        self.b.emit('done-reading', text, None)
        self.run_loop()
        assert len(self.t) == 2, [t[0] for t in self.t]
        task = self.t[0][0]
        self.assertEqual(text2, task.text)
        self.assertEqual(task.creation_date, None)

    def test_removal_from_blobstore_removes_tasks(self):
        self.b.open("abc 2020-04-03 a task t:2020-05-05")
        self.run_loop()
        assert len(self.t) == 1
        self.b.put("")
        self.b.emit('done-reading',"", None)
        self.run_loop()
        assert len(self.t) == 0

    def test_change_in_blobstore_changes_task(self):
        self.b.open("abc 2020-04-03 a task t:2020-05-05")
        self.run_loop()
        assert len(self.t) == 1
        task = self.t[0][0]
        # Simulate write to backend, and its side effect.
        text = "abc 2020-04-03 a task"
        self.b.put(text)
        self.b.emit('done-reading', text, None)
        self.run_loop()
        self.assertEqual(self.t[0][0].creation_date, datetime.date(2020, 4, 3))
        self.assertEqual(self.t[0][0].threshold_date, None)
        assert self.t[0][0] is task

    def test_adding_task_syncs_to_blobstore(self):
        task = "abc 2020-04-03 a task t:2020-05-05"
        self.b.open("")
        self.run_loop()
        assert len(self.t) == 0
        assert len(self.l) == 0
        self.t.append([ts.Task.fromstring(task)])
        self.run_loop()
        assert len(self.t) == 1
        assert len(self.l) == 1
        self.assertEqual(self.l[0][0], task)

    def test_removing_task_syncs_to_blobstore(self):
        self.b.open("abc 2020-04-03 a task t:2020-05-05")
        self.run_loop()
        assert len(self.t) == 1
        assert len(self.l) == 1, (len(self.l), [x[0] for x in self.l])
        self.t.remove(self.t.get_iter_first())
        self.run_loop()
        assert len(self.t) == 0
        assert len(self.l) == 0

    def test_changing_task_object_syncs_to_blobstore(self):
        self.b.open("abc 2020-04-03 a task t:2020-05-05")
        self.run_loop()
        changed_task = "abc 2020-04-03 a task"
        self.t[0][0] = ts.Task.fromstring(changed_task)
        self.t[0][0].connect("changed", self.t.on_task_changed)
        self.run_loop()
        self.assertEqual(self.t[0][0].threshold_date, None)
        self.b.put(self.l.serialize())
        self.run_loop()
        self.assertEqual(self.b.memory, changed_task)
        self.t[0][0] = self.t[0][0]
        self.run_loop()

    def test_changing_task_content_syncs_to_blobstore(self):
        self.b.open("abc 2020-04-03 a task t:2020-05-05")
        self.run_loop()
        changed_task = "abc 2020-04-03 a task"
        self.t[0][0].set_text(changed_task)
        self.run_loop()
        self.assertEqual(self.t[0][0].threshold_date, None)
        self.b.put(self.l.serialize())
        self.run_loop()
        self.assertEqual(self.b.memory, changed_task)

    def test_deleting_task_syncs_to_blobstore_and_mods_after_deletion_do_not_cause_errors(self):
        self.b.open("abc 2020-04-03 a task t:2020-05-05")
        self.run_loop()
        task = self.t[0][0]
        self.b.put("")
        self.run_loop()
        task.set_text("abc")
        self.run_loop()
        assert self.b.memory == ""
