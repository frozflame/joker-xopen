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
        super(XopenCacheServer, self).__init__()
        self.data = WarmConf(sizelimit, path)
        self.cached_commands = {b'#request'}
        self.commands = {
            b'#reload': self.cmd_reload,
            b'#update': self.cmd_update,
            b'#request': self.cmd_request,
            b'#version': self.cmd_version,
        }
        self._tpexec = ThreadPoolExecutor(max_workers=3)

    def lookup(self, key, val):
        if key in self.commands:
            return self._lookup_with_command(key, val)
        return super(XopenCacheServer, self).lookup(key, val)

    def _lookup_with_command(self, key, val):
        keyval = None
        if key in self.cached_commands:
            keyval = key + b'.' + val
            try:
                return self.data[keyval]
            except Exception:
                pass
        try:
            rv = self.commands[key](val)
        except Exception:
            traceback.print_exc()
            rv = self.val_none
        if key in self.cached_commands and rv:
            self.data[keyval] = rv
        return rv

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
    def cmd_request(url):
        return requests.get(url).content

    @staticmethod
    def cmd_version(_):
        import joker.xopen
        return 'joker-xopen==' + joker.xopen.__version__

    def cmd_reload(self, _):
        self._tpexec.submit(self.data.reload)

    def cmd_update(self, _):
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
