# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.


PROG_NAME = 'izdvd'
PROG_URL = 'https://github.com/izzilly/izdvd'
VIDEO_PLAYER = 'mplayer'
IMAGE_VIEWER = 'display'

RE_PARTS_SEP = r'[ _.-]'
RE_VOL_PREFIXES = r'cd|dvd|part|pt|disk|disc|d'
RE_VOL_NUMS = r'[0-9]'
RE_VOL_LETTERS = r'[a-d]'

MODE_NAMES = {'dvd':  'izdvd',
              'menu': 'izdvdmenu',
              'bg':   'izdvdbg'}
