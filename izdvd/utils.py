#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

import os.path
import argparse

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

