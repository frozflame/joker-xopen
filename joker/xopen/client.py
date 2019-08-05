#!/usr/bin/env python3
# coding: utf-8
import argparse
import os
import re

from volkanic.default import desktop_open


def get_port_num():
    envvar = 'JOKER_XOPEN_PORT'
    try:
        return int(os.environ.get(envvar))
    except TypeError:
        return 18831


def netcat(host, port, content):
    # https://stackoverflow.com/a/1909355/2925169
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        sock.sendall(content)
        sock.shutdown(socket.SHUT_WR)
        return sock.recv(2 ** 16)
    except Exception:
        return b''
    finally:
        sock.close()


def check_server():
    try:
        resp = netcat('127.0.0.1', get_port_num(), b'#version')
    except Exception:
        return False
    return resp.startswith(b'joker-xopen')


def get_api_url(target):
    prefix = 'https://a.geekinv.com/s/api/'
    return prefix + '.'.join(target.split())[:64]


def _openurl(url):
    if not re.match(r'https?://', url):
        return
    try:
        desktop_open(url)
    except Exception as e:
        from joker.cast.syntax import printerr
        printerr(e)


def _aopen_query_uncached(qs):
    import requests
    api_url = get_api_url(qs)
    url = requests.get(api_url).text
    _openurl(url)


def _aopen_query_cached(qs):
    api_url = get_api_url(qs)
    line = ('#request ' + api_url).encode('latin1')
    url = netcat('127.0.0.1', get_port_num(), line).decode('latin1')
    _openurl(url)


def aopen(*targets):
    if not targets:
        return
    if check_server():
        func = _aopen_query_cached
    else:
        func = _aopen_query_uncached
    if len(targets) == 1:
        return func(targets[0])
    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=4)
    return pool.map(func, targets)


def xopen(*targets):
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
    aopen(*indirect_locators)


def runxopen(prog=None, args=None):
    import sys
    if not prog and sys.argv[0].endswith('__main__.py'):
        prog = 'python3 -m joker.xopen'
    desc = 'xopen'
    pr = argparse.ArgumentParser(prog=prog, description=desc)
    aa = pr.add_argument
    aa('-d', '--direct', action='store_true', help='open all locators directly')
    aa('locator', nargs='*', help='URLs or filenames')
    ns = pr.parse_args(args)
    if ns.direct:
        return desktop_open(*ns.locator)
    xopen(*ns.locator)
