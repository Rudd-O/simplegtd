class ListStoreSyncer(object):

    list1 = None
    list2 = None

    def __init__(self, list1, list2, map_from_list1, map_from_list2):
        self.map = {
            list1: list2,
            list2: list1,
        }
        self.map_value = {
            list1: map_from_list1,
            list2: map_from_list2,
        }
        self.watches = {
            list1: [
                list1.connect('row-changed', self.on_row_changed),
                list1.connect('row-deleted', self.on_row_deleted),
                list1.connect('row-inserted', self.on_row_inserted),
                list1.connect('rows-reordered', self.on_rows_reordered),
            ],
            list2: [
                list2.connect('row-changed', self.on_row_changed),
                list2.connect('row-deleted', self.on_row_deleted),
                list2.connect('row-inserted', self.on_row_inserted),
                list2.connect('rows-reordered', self.on_rows_reordered),
            ]
        }

    def close(self):
        for lst, watches in self.watches.items():
            [lst.disconnect(w) for w in watches]

    def on_row_changed(self, source, path, iter_, *unused):
        dest = self.map[source]
        map_ = self.map_value[source]
        new_row = map_([x for x in source[iter_]])
        original_row = [x for x in dest[dest.get_iter(path)]]
        if new_row != original_row:
            dest.handler_block(self.watches[dest][0])
            dest[dest.get_iter(path)] = new_row
            dest.handler_unblock(self.watches[dest][0])

    def on_row_deleted(self, source, path, *unused):
        dest = self.map[source]
        dest.handler_block(self.watches[dest][1])
        dest.remove(dest.get_iter(path))
        dest.handler_block(self.watches[dest][1])

    def on_row_inserted(self, source, path, iter_, *unused):
        dest = self.map[source]
        map_ = self.map_value[source]
        new_row = map_([x for x in source[iter_]])
        source.handler_block(self.watches[source][2])
        dest.handler_block(self.watches[dest][2])
        dest.insert(path[0], new_row)
        dest.handler_unblock(self.watches[dest][2])
        source.handler_unblock(self.watches[source][2])

    def on_rows_reordered(self, source, *unused):
        dest = self.map[source]
        dest.handler_block(self.watches[dest][3])
        raise NotImplementedError
        dest.handler_unblock(self.watches[dest][3])
