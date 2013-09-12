#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

import os.path
import argparse
import tempfile
from datetime import datetime

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

def get_space_available(path):
    s = os.statvfs(path)
    return s.f_frsize * s.f_bavail

def get_out_paths(prog_name, out_name, out_dir, tmp_dir, tmp_required_space):
    # name
    if not out_name:
        out_time = datetime.now().strftime('%Y.%m.%d-%H%M%S')
        out_name = '{}_{}'.format(prog_name, out_time)
    
    # out dirs
    if not out_dir:
        out_dir = os.path.join(os.getcwd(), out_name)
    
    # tmp_dir
    if not tmp_dir:
        tmp = tempfile.gettempdir()
        tmp_free = get_space_available(tmp)
        if tmp_free > tmp_required_space:
            tmp_dir = os.path.join(tmp, prog_name, out_name)
        else:
            tmp_dir = os.path.join(out_dir, 'tmp')
    
    # make dirs if they don't exist
    for i in [out_dir, tmp_dir]:
        if not os.path.exists(i):
            os.makedirs(i)
    
    return out_name, out_dir, tmp_dir

def get_dvd_dims(ar, dvd_format):
    storage_width = 720
    if dvd_format.lower() == 'ntsc':
        storage_height = 480
        if ar == 16/9:
            display_width = 854
            display_height = 480
        elif ar == 4/3:
            display_width = 720
            display_height = 540
        else:
            raise
    elif dvd_format.lower() == 'pal':
        storage_height = 576
        display_height = 576
        if ar == 16/9:
            display_width = 1024
        elif ar == 4/3:
            display_width = 768
        else:
            raise
    dims = { 'storage_width':  storage_width,
             'storage_height': storage_height,
             'display_width':  display_width,
             'display_height': display_height }
    return dims


class HelpFormatter(argparse.HelpFormatter):
    def __init__(self,
                 prog,
                 indent_increment=2,
                 max_help_position=41,
                 width=None):
        # default setting for width
        if width is None:
            try:
                width,lines = os.get_terminal_size()
            except:
                width = 80
            width -= 2
        super(HelpFormatter, self).__init__(prog,
                                            indent_increment=indent_increment,
                                            max_help_position=max_help_position,
                                            width=width)
        
    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            metavar, = self._metavar_formatter(action, default)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)
            # if the Optional takes a value, format is:
            #    -s ARGS, --long ARGS
            else:
                default = self._get_default_metavar_for_optional(action)
                args_string = self._format_args(action, default)
                parts.append(', '.join(action.option_strings))
                parts.append(args_string)
            return ' '.join(parts)

