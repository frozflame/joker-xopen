#!/usr/bin/env python3
# coding: utf-8
import argparse
import os
import re

from volkanic.default import desktop_open
from joker.xopen import utils


class Client(object):
    def __init__(self, port=None):
        self.port = port or utils.get_port()

    def chksvr(self):
        return self.request(b'version').startswith(b'joker-xopen')

    def request(self, line):
        if isinstance(line, str):
            line = line.encode('utf-8')
        return utils.netcat('127.0.0.1', self.port, line)

    @staticmethod
    def sanitize(s, sep='.'):
        return sep.join(s.split())[:64]

    @staticmethod
    def get_api_url(target):
        prefix = 'https://a.geekinv.com/s/api/'
        return prefix + Client.sanitize(target)

    @staticmethod
    def desktop_open_url(url):
        if re.match(r'https?://', url):
            try:
                desktop_open(url)
            except Exception:
                pass

    @classmethod
    def _aopen_wapi(cls, qs):
        import requests
        api_url = cls.get_api_url(qs)
        url = requests.get(api_url).text
        cls.desktop_open_url(url)

    def _aopen(self, qs):
        resp = self.request(qs)
        if resp:
            return desktop_open(resp.decode('latin1'))
        api_url = self.get_api_url(qs)
        line = 'http-get ' + api_url
        url = self.request(line).decode('latin1')
        self.desktop_open_url(url)

    def aopen(self, *targets):
        if not targets:
            return
        f = self._aopen if self.chksvr() else self._aopen_wapi
        if len(targets) == 1:
            return f(targets[0])
        from concurrent.futures import ThreadPoolExecutor
        pool = ThreadPoolExecutor(max_workers=4)
        return pool.map(f, targets)


def _xopen(*targets):
    if not targets:
        return desktop_open('.')
    direct_locators = set()
    indirect_locators = set()
    exists = os.path.exists

    for t in targets:
        if exists(t) or re.match(r'(https?|file|ftp)://', t):
            direct_locators.add(t)
        elif re.match(r'[\w._-]{1,64}$', t):
            indirect_locators.add(t)
    desktop_open(*direct_locators)
    Client().aopen(*indirect_locators)


def _get_and_print(*keys):
    client = Client()
    for k in keys:
        v = client.request('get {}'.format(k)).decode()
        print(v)


def runxopen(prog=None, args=None):
    import sys
    if not prog and sys.argv[0].endswith('__main__.py'):
        prog = 'python3 -m joker.xopen'
    desc = 'joker-xopen client'
    pr = argparse.ArgumentParser(prog=prog, description=desc)
    aa = pr.add_argument
    aa('-g', '--get', action='store_true', help='get value from cache server')
    aa('-d', '--direct', action='store_true', help='open all locators directly')
    aa('-u', '--update', action='store_true', help='request server to update from tabfile')
    aa('locators', metavar='locator',
       nargs='*', help='keys, URLs or filenames')
    ns = pr.parse_args(args)
    if ns.update:
        # TODO: print msg
        Client().request(b'update')
    if ns.direct:
        return desktop_open(*ns.locators)
    if ns.get:
        return _get_and_print(*ns.locators)
    _xopen(*ns.locators)
