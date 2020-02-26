#!/usr/bin/env python3
# coding: utf-8

import os
import threading
from collections import OrderedDict


class LimitedDict(object):
    default_capacity = 2 ** 26

    def __init__(self, capacity=0, data=None):
        if not isinstance(data, OrderedDict):
            data = OrderedDict(data or {})
        self.data = data
        self.capacity = capacity or self.default_capacity
        self.freespace = capacity - self._estimate_size(self.data)
        self.evict()

    @staticmethod
    def _estimate_size(data):
        lengths = ((len(k) + len(v)) for k, v in data.items())
        return sum(lengths)

    def _reset(self, data):
        if not isinstance(data, OrderedDict):
            data = OrderedDict(data)
        with threading.Lock():
            self.data = data
            self.freespace = self.capacity - self._estimate_size(data)
            self.evict()

    def _update(self, data):
        with threading.Lock():
            self.data.update(data)
            for key in data:
                self.data.move_to_end(key, last=True)

    def pop(self, key, *default):
        val = self.data.pop(key, *default)
        if (val,) != default:
            self.freespace += len(key) + len(val)
        return val

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, val):
        pval = self.data.get(key, '')
        with threading.Lock():
            self.data[key] = val
            self.data.move_to_end(key, last=True)
            self.freespace += len(pval) - len(val)

    def get(self, key, default=None):
        return self.data.get(key, default)

    def evict(self):
        while self.freespace <= 0:
            self.data.popitem(last=False)


class ReconfDict(LimitedDict):
    comment = b'#'

    def __init__(self, capacity, *paths):
        _paths = {}
        for path in paths:
            path = os.path.expanduser(path)
            _paths[path] = self._getmtime(path)
        self.paths = _paths
        data = self.parse_many(*paths)
        LimitedDict.__init__(self, capacity, data)

    def __bool__(self):
        return True

    @staticmethod
    def _getmtime(path):
        return int(os.path.getmtime(path) * 1000)

    @classmethod
    def parse(cls, path):
        data = OrderedDict()
        with open(path, 'rb') as fin:
            for line in fin:
                line = line.strip()
                if not line or line.startswith(cls.comment):
                    continue
                parts = line.split(maxsplit=1)
                if len(parts) != 2:
                    continue
                k, v = parts
                data[k] = v
        return data

    @classmethod
    def parse_many(cls, *paths):
        data = OrderedDict()
        for path in paths:
            try:
                data.update(cls.parse(path))
            except (FileNotFoundError, IOError):
                continue
        return data

    def reload(self):
        updated = True
        for path, mtime in self.paths.items():
            real_mtime = self._getmtime(path)
            if real_mtime > mtime:
                updated = False
                break
        if not updated:
            data = self.parse_many(*self.paths)
            self._reset(data)

    def update(self):
        outdated = []
        for path, mtime in self.paths.items():
            real_mtime = self._getmtime(path)
            if real_mtime > mtime:
                outdated.append(path)
        if outdated:
            data = self.parse_many(*outdated)
            self._update(data)

