#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

import os.path

def read_file(path):
    with open(path) as f:
        data = f.read()
    return data

def write_file(data, path):
    with open(path, 'w') as f:
        f.write(data)

def read_int_file(path):
    data = read_file(path)
    val = int(data.strip())
    return val

def write_int_file(val, path):
    data = str(val)
    write_file(data, path)

def get_commonprefix(paths, sep='/'):
    cp = os.path.commonprefix(paths)
    in_all_paths = True
    for i in paths:
        if not cp.rstrip(sep)+sep in i.rstrip(sep)+sep:
            in_all_paths = False
            break
    if in_all_paths:
        return cp
    else:
        return cp.rpartition(sep)[0]

