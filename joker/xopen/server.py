#!/usr/bin/env python3
# coding: utf-8
import argparse
import os
import sys
import threading
import traceback
from collections import deque
from concurrent.futures import ThreadPoolExecutor

import requests
from joker.cast.syntax import printerr
from joker.minions.cache import CacheServer

from joker.xopen import utils
from joker.xopen.datatypes import LimitedDict, ReconfDict
from joker.xopen.environ import JokerInterface

ji = JokerInterface()


def _printerr(*args, **kwargs):
    parts = []
    for a in args:
        if isinstance(a, bytes):
            parts.append(a.decode())
        elif isinstance(a, (deque, list, tuple)):
            parts.extend(a)
    kwargs.setdefault('sep', ':')
    printerr(*parts, **kwargs)


def under_joker_xopen_dir(*paths):
    return ji.under_joker_subdir(*paths)


def get_default_source_paths():
    import glob
    xopen_dirpath = ji.under_joker_subdir(mkdirs=True)
    path = os.path.join(xopen_dirpath, 'xopen.txt')
    if not os.path.exists(path):
        with open(path, 'a'):
            pass
    patt = os.path.join(xopen_dirpath, '*.txt')
    return glob.glob(patt)


class _ReconfDict(ReconfDict):
    @classmethod
    def parse(cls, path):
        data = ReconfDict.parse(path)
        f = os.path.expanduser
        return {k: f(v) for k, v in data.items()}


class XopenCacheServer(CacheServer):
    def __init__(self, capacity, *paths):
        CacheServer.__init__(self)
        self.data = _ReconfDict(capacity, *paths)
        self.cache = LimitedDict(capacity, )
        self.cached_verbs = {b'http-get'}
        self.verbs = {
            b'reload': self.exec_reload,
            b'update': self.exec_update,
            b'version': self.exec_version,
            b'http-get': self.exec_http_get,
        }
        self._tpexec = ThreadPoolExecutor(max_workers=3)

    def _execute(self, verb, payload):
        try:
            return self.verbs[verb](payload)
        except Exception:
            traceback.print_exc()

    def _execute_with_cache(self, verb, payload):
        key = verb + b':' + payload
        try:
            return self.cache[key]
        except KeyError:
            pass
        rv = self._execute(verb, payload)
        self.cache[key] = rv
        return rv

    def execute(self, verb, payload):
        if verb in self.cached_verbs:
            return self._execute_with_cache(verb, payload)
        if verb in self.verbs:
            return self._execute(verb, payload)
        return CacheServer.execute(self, verb, payload)

    def _printdiff(self, vdata):
        udata = self.data.data
        keys = set(vdata)
        keys.update(udata)
        for k in keys:
            u = udata.get(k)
            v = vdata.get(k)
            if u != v:
                _printerr(k, u, v)

    @staticmethod
    def exec_http_get(url):
        return requests.get(url).content

    @staticmethod
    def exec_version(_):
        import joker.xopen
        return 'joker-xopen==' + joker.xopen.__version__

    def exec_reload(self, _):
        self._tpexec.submit(self.data.reload)

    def exec_update(self, _):
        self._tpexec.submit(self.data.update)

    def eviction(self, period=5):
        import time
        while True:
            time.sleep(period)
            self.cache.evict()
            self.data.evict()


def run(prog, args):
    import sys
    if not prog and sys.argv[0].endswith('server.py'):
        prog = 'python3 -m joker.xopen.server'
    desc = 'joker-xopen cache server'
    pr = argparse.ArgumentParser(prog=prog, description=desc)
    add = pr.add_argument

    add('-c', '--capacity', metavar='int',
        type=int, default=ReconfDict.default_capacity)

    add('sources', metavar='path', nargs='*',
        help='path to a source file, default `~/.joker/xopen/*.txt`')

    ns = pr.parse_args(args)
    sources = ns.sources or get_default_source_paths()

    # noinspection PyBroadException
    try:
        svr = XopenCacheServer(ns.capacity, *sources)
    except Exception:
        traceback.print_exc()
        sys.exit(1)
    threading.Thread(target=svr.eviction, daemon=True).start()
    svr.runserver('127.0.0.1', utils.get_port())


if __name__ == '__main__':
    run(None, sys.argv[1:])
