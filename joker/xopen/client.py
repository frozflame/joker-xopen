#!/usr/bin/env python3
# coding: utf-8
import argparse
import os
import re
import sys

from volkanic.default import desktop_open
from joker.xopen import utils


class Client(object):
    def __init__(self, port=None):
        self.port = port or utils.get_port()

    def chksvr(self):
        return self.request('version').startswith(b'joker-xopen')

    def request(self, qs):
        if isinstance(qs, str):
            qs = qs.encode('utf-8')
        elif isinstance(qs, bytes):
            pass
        else:
            qs = str(qs).encode('utf-8')
        return utils.netcat('127.0.0.1', self.port, qs)

    def get(self, key):
        return self.request('get ' + key).decode()

    def open(self, key):
        location = self.get(key)
        if location:
            return desktop_open(location)

    def open_many(self, *keys):
        if not keys:
            return
        if not self.chksvr():
            return
        if len(keys) == 1:
            return self.open(keys[0])

        from concurrent.futures import ThreadPoolExecutor
        pool = ThreadPoolExecutor(max_workers=4)
        return pool.map(self.open, keys)


def amphib_open(*locators):
    if not locators:
        return
    direct_locators = set()
    indirect_locators = set()
    exists = os.path.exists

    for loc in locators:
        if loc.startswith('~'):
            path = os.path.expanduser(loc)
            if os.path.exists(path):
                direct_locators.add(path)
                continue
        if exists(loc) or re.match(r'(https?|file|ftp)://', loc):
            direct_locators.add(loc)
        elif re.match(r'\S{1,64}$', loc):
            indirect_locators.add(loc)
    desktop_open(*direct_locators)
    Client().open_many(*indirect_locators)


def get_and_print(*keys):
    client = Client()
    for k in keys:
        v = client.get(k)
        print(v)


def request_and_printerr(qs):
    Client().request(qs)
    msg = "xopen client: '{}' request sent".format(qs)
    print(msg, file=sys.stderr)


def runxopen(prog=None, args=None):
    if not prog and sys.argv[0].endswith('__main__.py'):
        prog = 'python3 -m joker.xopen'
    desc = 'joker-xopen client'
    pr = argparse.ArgumentParser(prog=prog, description=desc)
    add = pr.add_argument

    add('-g', '--get', action='store_true',
        help='get value from cache server')

    add('-r', '--reload', action='store_true',
        help='request server to reload from conf')

    add('-u', '--update', action='store_true',
        help='request server to update from conf')

    add('locators', metavar='locator', nargs='*',
        help='key (in conf), pathname or url')

    ns = pr.parse_args(args)

    default_locators = ['.']
    if ns.reload:
        request_and_printerr('reload')
        default_locators = []

    if ns.update:
        request_and_printerr('update')
        default_locators = []

    locators = ns.locators or default_locators
    if ns.get:
        return get_and_print(*ns.locators)
    amphib_open(*locators)
