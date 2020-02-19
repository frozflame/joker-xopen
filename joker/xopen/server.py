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
from joker.minions.cache import CacheServer, WarmConf

from joker.xopen import utils


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
    from joker.default import under_joker_dir
    return under_joker_dir('xopen', *paths)


def get_tabfile_path():
    from joker.default import make_joker_dir
    path = os.path.join(make_joker_dir('xopen'), 'xopen.txt')
    with open(path, 'a'):
        return path


class XopenCacheServer(CacheServer):
    def __init__(self, sizelimit, path):
        CacheServer.__init__(self)
        self.data = WarmConf(sizelimit, path)
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
        key = verb + b'.' + playload
        try:
            return self.data[key]
        except Exception:
            pass
        rv = self._execute(verb, payload)
        self.data[key] = rv
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
            self.data.evict()


def run(prog, args):
    import sys
    if not prog and sys.argv[0].endswith('server.py'):
        prog = 'python3 -m joker.xopen.server'
    desc = 'joker-xopen cache server'
    pr = argparse.ArgumentParser(prog=prog, description=desc)
    aa = pr.add_argument
    aa('-s', '--size', type=int, default=WarmConf.default_sizelimit)
    aa('-t', '--tabfile', help='path to a 2-column tabular text file')
    ns = pr.parse_args(args)
    try:
        svr = XopenCacheServer(ns.size, ns.tabfile or get_tabfile_path())
    except Exception as e:
        printerr(e)
        sys.exit(1)
    threading.Thread(target=svr.eviction, daemon=True).start()
    svr.runserver('127.0.0.1', utils.get_port())


if __name__ == '__main__':
    run(None, sys.argv[1:])
