import contextlib
import os
import tempfile
import threading
import time
import unittest

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import GLib

import simplegtd.models.blobstore as bs
import simplegtd.models.linestore as sm


def fixture_path(name):
    return os.path.join(os.path.dirname(__file__), "fixtures", name)


def fixture_text(name):
    with open(fixture_path(name), "r") as f:
        return f.read()


def fixture_list(name):
    return [x for x in fixture_text(name).splitlines()]


def dump(liststore):
    elements = []
    for row in liststore:
        elements.append(row[0])
    return elements


@contextlib.contextmanager
def ctx(kallable):
    obj = kallable()
    try:
        yield obj
    finally:
        if hasattr(obj, "close"):
            obj.close()


def transform_file_text(fobject, before_list, after_list, flush):
    assert len(before_list) <= len(after_list)
    working_list = list(before_list)
    fobject.seek(0)
    fobject.truncate(0)
    fobject.write("\n".join(working_list))
    yield 0
    for n, (new) in enumerate(after_list):
        try:
            working_list[n] = new
        except IndexError:
            working_list.append(new)
        fobject.seek(0)
        fobject.truncate(0)
        fobject.write("\n".join(working_list))
        if flush:
            fobject.flush()
        yield n + 1
    assert working_list == after_list


def gloop():
    store = []
    c = GLib.MainContext.default()
    collector = lambda *a: store.append(a)
    def evac(pos):
        while c.pending() or not store:
            c.iteration(False)
        val = store[0][pos]
        store.clear()
        return val
    return collector, evac


def check_exc(datum):
        if isinstance(datum, Exception):
            raise datum


class LineStoreTest(unittest.TestCase):

    def test_loads_fine_from_string_blobstore(self):
        with ctx(lambda: bs.StringBlobStore()) as b:
            with ctx(lambda: sm.LineStore()) as t:
                b.connect("done-reading", t.unserialize),
                b.open(fixture_text("before.txt"))
                gloop()
                loaded = dump(t)
                read = fixture_list("before.txt")
                self.assertListEqual(loaded, read)

    def test_loads_fine(self):
        with ctx(lambda: bs.FileBlobStore()) as b:
            with ctx(lambda: sm.LineStore()) as t:
                b.connect("done-reading", t.unserialize),
                collect, result = gloop()
                b.connect("done-reading", collect)
                b.open(fixture_path("before.txt"))
                check_exc(result(2))
                self.assertListEqual(dump(t), fixture_list("before.txt"))

    def test_loads_written_text_from_another_process(self):
        with tempfile.NamedTemporaryFile(mode="w+") as f:
            with ctx(lambda: bs.FileBlobStore()) as b:
                with ctx(lambda: sm.LineStore()) as t:
                    b.connect("done-reading", t.unserialize),
                    collect, result = gloop()
                    self.assertListEqual(dump(t), [])
                    b.connect("done-reading", collect)
                    b.open(fixture_path("before.txt"))
                    f.write(fixture_text("before.txt"))
                    f.flush()
                    check_exc(result(2))
                    self.assertListEqual(dump(t), fixture_list("before.txt"))

    def _test_transform_line_by_line_in_mainloop(self, flush):
        before_list = fixture_list("before.txt")
        after_list = fixture_list("after.txt")
        def file_writer(f, flush):
            def target():
                for unused_linenumber in transform_file_text(f, before_list, after_list, flush):
                    time.sleep(0.001)
            return threading.Thread(target=target)

        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(mode="w+", dir=tmpdir) as f:
                with ctx(lambda: bs.FileBlobStore()) as b:
                    with ctx(lambda: sm.LineStore()) as t:
                        b.connect("done-reading", t.unserialize),
                        th = file_writer(f, flush)
                        c = GLib.MainContext.default()
                        b.open(f.name)
                        th.start()
                        while c.pending() or dump(t) != after_list:
                            c.iteration(False)
                            time.sleep(0.05)
                        th.join()
                        x = os.stat(f.name)
                        last_changed = (getattr(x, "st_mtime_ns", x.st_mtime), getattr(x, "st_ctime_ns", x.st_ctime), x.st_size)
                        self.assertListEqual(
                            dump(t), after_list,
                            "Comparison failed.  Object last changed: %s.  Actual last changed: %s." % (
                                b._last_changed,
                                last_changed
                            )
                        )

    def test_transform_line_by_line_in_mainloop_with_flushing(self):
        return self._test_transform_line_by_line_in_mainloop(True)

    def test_transform_line_by_line_in_mainloop_without_flushing(self):
        return self._test_transform_line_by_line_in_mainloop(False)
