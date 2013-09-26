#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

import numbers


def prompt_user(question, answers):
    pass

def prompt_user_list(choices, prompt=None,
                     header='User input required', 
                     default=0, info=None,
                     include_quit=True, quit_def=('q', 'quit'), 
                     lines_before=1, choices_sep='-', sep_length=78):
    print('\n'*lines_before)
    if header:
        print('{}:'.format(header))
    if prompt is None:
        prompt = 'Select from the choices above [{}]: '.format(default)
    idx_width = len(str(len(choices)))
    choices = '\n'.join(['{:{width}}) {}'.format(n, i, width=idx_width) 
                         for n,i in enumerate(choices)])
    if include_quit:
        choices = '\n'.join([choices, '{}) {}'.format(*quit_def)])
    if choices_sep:
        print(choices_sep*sep_length)
    print(choices)
    if choices_sep:
        print(choices_sep*sep_length)
    while True:
        response = input(prompt).lower()
        if response == '':
            return default
        if response == 'q':
            return False
        if response.isdigit():
            response = int(response)
        if response in range(len(choices.splitlines())):
            return int(response)
        else:
            print('Invalid choice.')


