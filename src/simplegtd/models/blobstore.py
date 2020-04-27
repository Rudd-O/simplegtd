import errno
import logging
import os
import threading

import gi
gi.require_version('GObject', '2.0')
gi.require_version('Gtk', '3.0')
from gi.repository import GLib, GObject, Gio


class AbstractBlobStore(GObject.GObject):
    '''An AbstractBlobStore is an object type that presents an interface to
    views, which are interested in data from a source (e.g. a file, or a block
    of memory, and want to obtain its contents, as well as get notified in an
    asynchronous manner when the data is being obtained.

    The BlobStore emits several signals:

    1. `reading`, when the source has changed, and the BlobStore is about
       to re-read the source in order to obtain the data.
    2. `done-reading`, when the BlobStore is finished reading the source.
       Two parameters accompany the signal:
       a) the data if successfully read (None if unsuccessful).
       b) the exception that happened, if unsuccessful (none, if successful).
    3. `writing`, when the object has been told to save the data to the
       source via put().
    4. `done-writing`, when the object is done saving the data to the source.
       One parameter accompanies the signal:
       a) the data that was just written.
       a) None if the save was successful, an exception if the save failed.

    Subscribers should subscribe to both signals to know when it is safe to
    call store() -- subscribers should not call store() in between the emission
    of the `reading` and the `done-reading` signal.
    '''

    __gsignals__ = {
        'reading': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'done-reading': (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
        'writing': (GObject.SIGNAL_RUN_FIRST, None, ()),
        'done-writing': (GObject.SIGNAL_RUN_FIRST, None, (object, object)),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

    def open(self, source):
        '''Opens the source, creating if it does not exist.  Immediately after
        calling open(), the signals `reading` and then `done-reading` will be
        emitted.

        The meaning of the `source` parameter depends upon the implementation
        of the subclass.

        Emits an exception (via the `done-reading` signal) if it could not
        open or create the source.

        If an exception is emitted, the caller should assume this object is
        invalid, disconnect all the connections it made, and discard this
        object altogether.

        You cannot open() an object twice.
        '''
        raise NotImplementedError

    def close(self):
        '''Closes the source, finishing monitoring of file changes.

        No signals will be raised after closing the source.  It is an error
        to call put() after close().

        Raises an exception if it could not open the source and it could also
        not create the source (if it didn't exist).
        '''
        raise NotImplementedError

    def put(self, data):
        '''Store data in the source.

        Emits an exception (via the `done-writing` signal) if it could not
        store the data successfully.  If an exception is emitted, unless
        it is an IOError(EBUSY), the caller should assume further tries to
        put() data to the object will fail.

        It is a ValueError to call put() in between the `reading` and
        `done-reading` signals.
        '''
        raise NotImplementedError


class StringBlobStore(AbstractBlobStore):

    memory = None
    __closed = False

    def open(self, source):
        (
            AbstractBlobStore.open.__doc__,
            '''

        This implementation uses the string representation of the `source`
        parameter to initialize its memory.
        '''
        )
        if self.memory is not None:
            raise ValueError("open() operation on opened %s" % self.__class__.__name__)
        if self.__closed:
            raise ValueError("open() operation on closed %s" % self.__class__.__name__)
        self.memory = str(source) or ''
        self.emit('reading')
        self.emit('done-reading', self.memory, None)

    def close(self):
        self.__closed = True
        self.memory = None

    def put(self, data):
        (
            AbstractBlobStore.put.__doc__,
            '''

        This implementation stores the string representation of the `data`
        parameter in its memory.
        '''
        )
        if self.memory is None:
            raise ValueError("put() operation on unopened %s" % self.__class__.__name__)
        if self.__closed:
            raise ValueError("put() operation on closed %s" % self.__class__.__name__)
        self.emit("writing")
        self.memory  = str(data)
        self.emit("done-writing", data, None)


class FileBlobStore(AbstractBlobStore):

    name = None
    __closed = False
    _last_changed = (-1, -1, -1)
    __file_changes_detected = 0
    __monitor_dir = None
    __monitor_handle = None
    __loading = False

    def __init__(self):
        AbstractBlobStore.__init__(self)
        self.logger = logging.getLogger(self.__class__.__name__)

    def open(self, source):
        (
            AbstractBlobStore.open.__doc__,
            '''

        This implementation uses a file named in the `source` parameter,
        creating the file if it does not exist.
        '''
        )
        if self.name is not None:
            raise ValueError("open() operation on opened %s" % self.__class__.__name__)
        if self.__closed:
            raise ValueError("open() operation on closed %s" % self.__class__.__name__)

        self.name = source
        self.__begin_watching()
        self._load()

    def __begin_watching(self):
        assert not self.__monitor_handle
        giofile_dir = Gio.File.new_for_path(os.path.dirname(self.name))
        self.__monitor_dir = giofile_dir.monitor(Gio.FileMonitorFlags.WATCH_MOVES, None)
        self.__monitor_handle = self.__monitor_dir.connect("changed", self.__dir_changed)

    def __pause_watching(self):
        self.__monitor_dir.disconnect(self.__monitor_handle)
        self.__monitor_handle = None
        self.__monitor_dir.cancel()
        self.__monitor_dir = None

    def __dir_changed(self, unused_monitor, unused_f, newf, event):
        if self.__closed:
            return
        if self.__loading:
            return
        self.__file_changes_detected += 1
        if event == Gio.FileMonitorEvent.CHANGES_DONE_HINT:
            self.logger.debug("Directory changed.  Reloading.")
            self._load()
        elif event == Gio.FileMonitorEvent.RENAMED:
            if newf.get_basename() == os.path.basename(self.name):
                self.logger.debug("A file was renamed to %s.  Reloading." % self.name)
                self._load()

    # FIXME: block edits while loading.
    # And block edits while saving.
    def _load(self, previously_read_data=False):
        if self.__closed:
            # File was closed in between speculative loads.
            # Simply ignore this.
            return False
        if previously_read_data is False:
            self.__loading = True
            self.emit("reading")
            self.logger.debug("About to read %s" % self.name)

        try:
            try:
                with open(self.name, "r") as f:
                    statf = os.stat(self.name)
                    data = f.read()
            except FileNotFoundError:
                with open(self.name, "w"):
                    pass

            if previously_read_data is False:
                # We're going to wait a bit and reload, mainly to
                # see if the file's contents are stable over some time.
                self.logger.debug('Waiting a bit to re-read %s before we declare success.', self.name)
                GLib.timeout_add(75, lambda: self._load(data) and False)
            elif data == previously_read_data:
                # The file's contents have remained stable.
                # We can truly load now.
                self.logger.debug('File %r is stable now, truly reloading.', self.name)
                self._last_changed = (getattr(statf, "st_mtime_ns", statf.st_mtime), getattr(statf, "st_ctime_ns", statf.st_ctime), statf.st_size)
                self.__loading = False
                self.logger.debug("Done reading %s" % self.name)
                self.emit("done-reading", data, None)
                return False
            else:
                # Uh-oh, the file changed from under us.
                # We must once again re-run this.
                self.logger.debug('File %r changed from under us while we were loading, waiting again.', self.name)
                GLib.timeout_add(75, lambda: self._load(data) and False)

        except Exception as e:
            self.__loading = False
            self.logger.debug("Error reading %s: %s" % (self.name, e))
            self.emit("done-reading", None, e)

    def close(self):
        if self.__monitor_handle:
            self.__monitor_dir.disconnect(self.__monitor_handle)
        if self.__monitor_dir:
            self.__monitor_dir.cancel()
        self.__closed = True
        self.name = None

    def put(self, data):
        (
            AbstractBlobStore.put.__doc__,
            '''

        This implementation stores the string representation of the `data`
        parameter in the file named in open().

        If the file is in the middle of reading because it changed, `done-reading`
        emits IOError(errno.EAGAIN).  Caller must attempt to put() again later,
        or preferably cancel/undo the operation that started the put(), because
        data loss is likely (overwrite of out-of-date data).
        '''
        )
        if self.name is None:
            raise ValueError("put() operation on unopened %s" % self.__class__.__name__)
        if self.__closed:
            raise ValueError("put() operation on closed %s" % self.__class__.__name__)
        if self.__closed:
            raise ValueError("put() operation on closed %s" % self.__class__.__name__)
        if self.__loading:
            raise IOError(errno.EAGAIN, "put() operation on busy %s" % self.__class__.__name__)

        self.__pause_watching()
        self.emit("writing")
        self.logger.debug("About to write %s" % self.name)

        def _finish_put(name, new_data):
            try:
                with open(name, "w+") as f:
                    if new_data == f.read():
                        self.logger.debug("Unchanged.  No writes.")
                    else:
                        f.seek(0)
                        f.truncate()
                        f.write(new_data)
                        f.flush()
                self.logger.debug("Done writing %s" % name)
                l1 = lambda: self.emit("done-writing", new_data, None)
                l2 = lambda: self.__begin_watching()
                GObject.idle_add(l1)
                GObject.idle_add(l2)
            except Exception as e:
                self.logger.debug("Error writing %s: %s" % (self.name, e))
                l1 = lambda: self.emit("done-writing", None, e)
                l2 = lambda: self.__begin_watching()
                GObject.idle_add(l1)
                GObject.idle_add(l2)

        t = threading.Thread(target=_finish_put, args=(self.name, data))
        t.start()
