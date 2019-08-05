#!/usr/bin/env python3
# coding: utf-8

import os


def get_port():
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

