#!/usr/bin/env python3
# coding: utf-8

import os


def get_port_num():
    envvar = 'JOKER_XOPEN_PORT'
    try:
        return int(os.environ.get(envvar))
    except TypeError:
        return 18831
