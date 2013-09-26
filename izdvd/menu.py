#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

from izdvd.image import Img, CanvasImg, TextImg
from izdvd.encoder import Encoder
from izdvd import utils
from izdvd import user_input
import sys
import tempfile
import subprocess
import math
from collections import Counter
import argparse
from datetime import datetime, timedelta
import os
from lxml import etree
import glob
import re
import logging
import numbers
import textwrap

PROG_NAME = 'izdvd'
VIDEO_PLAYER = 'mplayer'
IMAGE_VIEWER = 'display'

RE_PARTS_SEP = r'[ _.-]'
RE_VOL_PREFIXES = r'cd|dvd|part|pt|disk|disc|d'
RE_VOL_NUMS = r'[0-9]'
RE_VOL_LETTERS = r'[a-d]'

logger = logging.getLogger()
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

def log_items(items=None, heading=None, lvl=logging.INFO, 
              sep='=', sep_length=78, max_width=78, s_indent=4, indent=0, 
              col_width=12, lines_before=0, lines_after=0, 
              sep_pre=None, sep_post=None):
    for l in range(lines_before):
        logger.log(lvl, '')
    if heading:
        logger.log(lvl, sep*sep_length)
        logger.log(lvl, heading)
        logger.log(lvl, sep*sep_length)
    if sep_pre:
        logger.log(lvl, sep_pre*sep_length)
        
    if items is False:
        return
    if items is None:
        items = ['<none>']
    if isinstance(items, numbers.Number):
        items = str(items)
    if type(items) == str:
        items = [items]
    for i in items:
        if i is None:
            i = ''
        if type(i) == tuple:
            lines = []
            item = i[0]
            val = i[1] if i[1] is not None else '<none>'
            if isinstance(val, numbers.Number):
                val = str(val)
            if type(val) == str:
                val = [val]
            for n,v in enumerate(val):
                if n == 0:
                    c1 = item+' : '
                    sep = ': '
                else:
                    c1 = ''
                    sep = '  '
                msg = '{c1:>{width}}{c2}'.format(c1=c1, c2=v,
                                                width=col_width+3)
                lines.append(msg)
        else:
            lines = [i]
        for l in lines:
            if indent:
                l = textwrap.indent(l, ' '*indent)
            logger.log(lvl, l)
    if sep_post:
        logger.log(lvl, sep_post*sep_length)
    for l in range(lines_after):
        logger.log(lvl, '')

def get_space_available(path):
    s = os.statvfs(path)
    return s.f_frsize * s.f_bavail


class BG (object):
    def __init__(self, 
                 # input paths
                 menu_imgs, 
                 menu_bg=None,
                 menu_labels=None,
                 # output paths 
                 out_name=None,
                 out_dir=None,
                 tmp_dir=None,
                 # ---------------bg opts --------------------
                 # padding
                 outer_padding=30, 
                 inner_padding=30,
                 label_padding=5, 
                 # size/shape 
                 display_width=None, 
                 display_height=None, 
                 menu_ar=None,
                 storage_ar=None,
                 dvd_format='NTSC',
                 # buttons
                 button_border_color='white', 
                 button_border_thickness=5, 
                 button_highlight_color='#56B356', 
                 button_highlight_thickness=10,
                 button_select_color='red',
                 shadow_sigma=3, 
                 shadow_x_offset=5, 
                 shadow_y_offset=5,
                 # labels
                 label_line_height=0, 
                 label_lines=2
                 ):
        # input paths
        self.menu_bg = menu_bg
        self.menu_imgs = menu_imgs
        self.menu_labels = menu_labels
        # output paths        
        self.out_name = out_name
        self.out_dir = out_dir
        self.tmp_dir = tmp_dir
        # padding
        self.label_padding = label_padding
        self.outer_padding = outer_padding
        self.inner_padding = inner_padding
        # size/shape
        self.display_width = display_width
        self.display_height = display_height
        if type(menu_ar) == str:
            ar_w, ar_h = menu_ar.split(':')
            menu_ar = int(ar_w) / int(ar_h)
        self.menu_ar = menu_ar
        self.storage_ar = storage_ar
        self.dvd_format = dvd_format
        # buttons
        self.button_border_color = button_border_color
        self.button_border_thickness = button_border_thickness
        self.button_highlight_color = button_highlight_color
        self.button_highlight_thickness = button_highlight_thickness
        self.button_select_color = button_select_color
        self.shadow_sigma = shadow_sigma
        self.shadow_x_offset = shadow_x_offset
        self.shadow_y_offset = shadow_y_offset
        # labels
        self.label_line_height = label_line_height
        self.label_lines = label_lines
        #---------
        self.get_out_paths()
        self.get_imgs()
        self.get_dims()
        self.make_bg()
        self.resize_bg()
        if self.button_imgs is not None:
            self.calc_cell_ar()
            self.get_grid_size()
            self.resize_buttons()
            self.create_labels()
            self.prepare_buttons()
            self.append_labels()
            self.apply_shadows()
            self.get_cell_locations()
            self.overlay_buttons()
        self.resize_imgs()
        self.write()
    
    def get_out_paths(self):
        paths = utils.get_out_paths(PROG_NAME, self.out_name, self.out_dir,
                                    self.tmp_dir, 50*1024*1024)
        self.out_name, self.out_dir, self.tmp_dir = paths
        self.out_files_dir = os.path.join(self.out_dir, 'files')
        fdir = self.out_files_dir
        out_name = self.out_name
        
        self.path_bg_img = os.path.join(fdir, '{}_bg.png'.format(out_name))
        self.path_hl_img = os.path.join(fdir, '{}_hl.png'.format(out_name))
        self.path_sl_img = os.path.join(fdir, '{}_sl.png'.format(out_name))
        self.path_hl_lb_img = os.path.join(fdir, 
                                           '{}_hl_lb.png'.format(out_name))
        self.path_sl_lb_img = os.path.join(fdir, 
                                           '{}_sl_lb.png'.format(out_name))
    
    def get_imgs(self):
        if self.menu_imgs:
            self.button_imgs = [Img(i) for i in self.menu_imgs]
        else:
            self.button_imgs = None
        if self.menu_bg and os.path.exists(self.menu_bg):
            self.bg_img = Img(self.menu_bg)
        else:
            self.bg_img = None
    
    def get_dims(self):
        if self.menu_ar and self.dvd_format:
            dims = utils.get_dvd_dims(self.menu_ar, self.dvd_format)
            self.storage_width = dims['storage_width']
            self.storage_height = dims['storage_height']
            self.display_width = dims['display_width']
            self.display_height = dims['display_height']
            self.display_ar = self.menu_ar
            self.storage_ar = self.storage_width / self.storage_height
        else:
            self.display_width = self.bg_img.get_width()
            self.display_height = self.bg_img.get_height()
            self.display_ar = self.display_width / self.display_height
            if self.storage_ar is None:
                self.storage_ar = self.display_ar
                self.storage_width = self.display_width
                self.storage_height = self.display_height
            else:
                multiplier = self.storage_ar / self.display_ar
                self.storage_width = self.display_width * multiplier
                self.storage_height = self.display_height
    
    def make_bg(self):
        if self.bg_img is None:
            if self.menu_bg is not None:
                try:
                    self.bg_img = CanvasImg(width=self.display_width,
                                            height=self.display_height,
                                            color=self.menu_bg)
                    return
                except:
                    pass
            self.bg_img = CanvasImg(width=self.display_width,
                                    height=self.display_height,
                                    color='gray')
    
    def resize_bg(self):
        if self.bg_img.get_width() != self.display_width:
            new_width = self.display_width
        else:
            new_width = None
        if self.bg_img.get_height() != self.display_height:
            new_height = self.display_height
        else:
            new_height = None
        if new_width or new_height:
            self.bg_img.resize(width=new_width, height=new_height,
                               ignore_aspect=True)
    
    def calc_cell_ar(self):
        '''Gets the most common aspect ratio of all button images.
        
        Buttons with any other a/r will be padded to fit in a cell 
        with this a/r.
        
        Returns:    aspect ratio (float)
                        (corrected for any difference between storage 
                         and display aspect ratios.)
        '''
        ars = Counter([i.ar for i in self.button_imgs])
        base_ar = ars.most_common()[0][0]
        self.cell_ar = base_ar
    
    def get_grid_size(self):
        '''Determines the optimal layout of rows and columns (i.e., the grid
        size which maximizes the size of the buttons).
        
        Returns:    a dict containing: 
                        the number of rows/columns,
                        the cell width/height
                        the total area of all cells
                        the empty space leftover
        
        # Info about the calculations:
            bg_ar / cell_ar = cols / rows
                              (grid_ratio)
            buttons = cols * rows
            
            buttons = rows(gr*rows)
            buttons = gr * rows^2self.width
            buttons / gr = rows^2
            sqrt(buttons / gr) = rows
            
            buttons = cols * (cols/gr)
            buttons = cols^2/gr
            buttons*gr = cols^2
            sqrt(buttons*gr) = cols
        '''
        bg_w = self.display_width - self.outer_padding*2
        bg_h = self.display_height - self.outer_padding*2
        bg_ar = bg_w / bg_h
        grid_ratio = bg_ar / self.cell_ar
        buttons = len(self.button_imgs)
        initial_rows = math.floor(math.sqrt(buttons / grid_ratio))
        initial_cols = math.floor(math.sqrt(buttons * grid_ratio))
        max_area = 0
        min_empty = 9999
        max_methods = []
        tied_methods = []
        results = []
        methods = [{'name': 'DD', 'rounding': (0,0)}, 
                   {'name': 'DU', 'rounding': (0,1)},
                   {'name': 'UD', 'rounding': (1,0)},
                   {'name': 'UU', 'rounding': (1,1)}]
        for i in methods:
            cols = initial_cols+i['rounding'][0]
            rows = initial_rows+i['rounding'][1]
            empty = cols*rows - buttons
            i['empty'] = empty
            if empty >= 0:
                area, bw, bh = self.get_cell_size(cols, rows, self.cell_ar,
                                                  bg_w, bg_h)
                i['cols'] = cols
                i['rows'] = rows
                i['area'] = area
                i['empty'] = empty
                i['cell_w'] = bw
                i['cell_h'] = bh
        sufficient = [i for i in methods if i['empty'] > -1]
        areas = sorted([i['area'] for i in sufficient])
        max_area = areas[-1]
        max_methods = [i for i in sufficient if i['area'] == max_area]
        mm_empty = sorted([i['empty'] for i in max_methods])
        least_empty = mm_empty[0]
        best_methods = [i for i in max_methods if i['empty'] == least_empty]
        tied_methods = [i for i in max_methods if i not in best_methods]
        other_methods = [i for i in sufficient if i not in max_methods]
        best = best_methods[0]
        self.grid = best
        self.cols = best['cols']
        self.rows = best['rows']
        self.cell_w = best['cell_w']
        self.cell_h = best['cell_h']
        return best_methods[0]
    
    def get_cell_size(self, cols, rows, cell_ar, bg_w, bg_h):
        '''Get the size of a single cell at a given grid size
            (number of rows/columns, cell aspect ratio, and total width/height)
        
        Returns:    area        (float)
                    cell width  (float; rounded down to nearest pixel)
                    cell height (float; rounded down to nearest pixel)
        '''
        padding_w = self.inner_padding * (cols - 1)
        padding_h = self.inner_padding * (rows - 1)
        label_padding_h = (self.label_line_height*self.label_lines 
                           + self.label_padding) * rows
        shadow_padding = self.calculate_shadow_padding()
        shadow_padding_x = shadow_padding['x']
        shadow_padding_y = shadow_padding['y']
        padded_w = bg_w - padding_w - shadow_padding_x
        padded_h = bg_h - padding_h - label_padding_h - shadow_padding_y
        col_w = padded_w / cols
        row_h = padded_h / rows
        cell_w = col_w
        cell_h = cell_w/cell_ar
        if cell_h > row_h:
            cell_h = row_h
            cell_w = cell_h*cell_ar
        return cell_w*cell_h, math.floor(cell_w), math.floor(cell_h)
    
    def calculate_shadow_padding(self):
        '''
        Calculates the increase in size that will result from applying
        a drop shadow to the button images.
        
        The sigma option increases the size by 2*sigma in all four directions,
        but along 2 of the images 4 edges, this increase can be reduced by 
        the x_offset and y_offset options.  
        
        Basically, a new image will be created that is 2*sigma larger in all 
        four directions, then that image will be layered below the original
        image, aligned according to x and y offsets.  So with a zero offset
        in a given direction, the image would grow by 4*sigma (2*sigma on both
        sides) but any non-zero offset will cause one side to grow by 2*sigma
        and the other to grow an amount between 0 and 2*sigma (if the offset 
        in that given direction is greater than or equal to 2*sigma, then it 
        would be 0, because it cannot shrink, else it would be 2*sigma minus
        the offset).
        '''
        
        sigma = self.shadow_sigma * 2
        # north/west movements above zero have no effect
        north = abs(min([sigma*-1 + self.shadow_y_offset, 0]))
        west = abs(min([sigma*-1 + self.shadow_x_offset, 0]))
        # south/east movements below zero have no effect
        south = max([sigma + self.shadow_y_offset, 0])
        east = max([sigma + self.shadow_x_offset, 0])
        shadow_padding = {'y': north + south,
                          'x': west + east,
                          'north': north,
                          'south': south,
                          'east': east,
                          'west': west}
        return shadow_padding
    
    def resize_buttons(self):
        '''Resize each button image to fit into the aspect ratio stored in
        self.cell_ar and corrects for any difference between storage and 
        display aspect ratios.
        
        Returns:    None
                        (modifies self.button_imgs)
        '''
        for i in self.button_imgs:
            if i.ar > self.cell_ar:
                w = self.cell_w
                h = math.floor(self.cell_w / self.cell_ar)
                i.x_padding = 0
                i.y_padding = math.floor((self.cell_h - h) / 2)
            elif i.ar < self.cell_ar:
                w = math.floor(self.cell_h * self.cell_ar)
                h = self.cell_h
                i.x_padding = math.floor((self.cell_w - w) / 2)
                i.y_padding = 0
            else:
                w = self.cell_w
                h = self.cell_h
                i.x_padding = 0
                i.y_padding = 0
            i.resize(w, h, True)
    
    def prepare_buttons(self):
        '''Add border and shadow to each button and create new outline images
        for the hightlight/select subtitles used for moving the cursor around
        the menu and selecting a button.
        
        Returns:    None
                        (modifies self.button_imgs and adds the 
                         highlight/select images as an attribute to each.)
        '''
        for i in self.button_imgs:
            hl = i.new_canvas()
            hl.border(1, shave=True)
            hl.border(self.button_highlight_thickness, 
                      self.button_highlight_color)
            i.highlight = hl
            sl = i.new_canvas()
            sl.border(1, shave=True)
            sl.border(self.button_highlight_thickness, 
                      self.button_select_color)
            i.select = sl
            i.border(self.button_border_thickness, self.button_border_color)
    
    def create_labels(self):
        '''Create images for each label to be placed alongside the button 
        images.
        '''
        has_labels = [i for i in self.menu_labels if i]
        if not has_labels:
            self.menu_labels = None
        if not self.menu_labels or not self.label_line_height > 0:
            self.label_imgs = None
            self.label_height = 0
            self.label_padding = 0
            return False
        button_w = max([i.get_width() for i in self.button_imgs])
        labels = []
        for i in self.menu_labels:
            img = TextImg(i, line_height=self.label_line_height, 
                                  max_width=button_w, 
                                  max_lines=self.label_lines,
                                  strokewidth=4)
            labels.append(img)
        self.label_height = max([i.get_height() for i in labels])
        for i in labels:
            if i.get_height() < self.label_height:
                i.pad_to(new_h=self.label_height, gravity='center')
        self.label_imgs = labels
    
    def append_labels(self):
        '''Appends label images to button images to create a new image 
        containing both.
        '''
        if self.label_imgs:
            for n,img in enumerate(self.button_imgs):
                img.append([self.label_imgs[n]], padding=self.label_padding)
    
    def apply_shadows(self):
        for i in self.button_imgs:
            i.drop_shadow(sigma=self.shadow_sigma, 
                          x_offset=self.shadow_x_offset,
                          y_offset=self.shadow_y_offset)
    
    def get_cell_locations(self):
        '''Get the coordinates at which to place each button
        
        Returns:    cell locations (dict)
                        x0: left edge
                        y0: top edge
                        x1: right edge
                        y1: bottom edge
        '''
        cells = len(self.button_imgs)
        cols = self.cols
        rows = self.rows
        label_height = self.label_height
        shadow_padding = self.calculate_shadow_padding()
        cell_w = self.cell_w + shadow_padding['x']
        # TODO: ensure cell_h is correct when no labels; i.e., 
        # label_height/label_padding needs to be zero if there is no label.
        cell_h = (self.cell_h + label_height 
                  + self.label_padding + shadow_padding['y'])
        bg_w = self.display_width
        bg_h = self.display_height
        total_cells = list(range(cells))
        cells = []
        padding_y = math.floor((bg_h - cell_h*rows) / (rows + 1))
        padded_y = cell_h + padding_y
        for r in range(rows):
            row_cells = total_cells[len(cells):len(cells)+cols]
            len_cells = len(row_cells)
            padding_x = math.floor((bg_w - cell_w*len_cells) / (len_cells + 1))
            padded_x = cell_w + padding_x
            for rc in range(len_cells):
                x0 = padding_x + (rc*padded_x)
                x1 = x0 + cell_w
                y0 = padding_y + (r*padded_y)
                y1 = y0 + cell_h
                c = {'x0': x0, 'y0': y0, 'x1': x1, 'y1': y1}
                cells.append(c)
        self.cell_locations = cells
    
    def overlay_buttons(self):
        '''Overlays the buttons onto the background image.
        '''
        if self.button_imgs is None:
            return
        self.highlight_img = self.bg_img.new_canvas()
        self.select_img = self.bg_img.new_canvas()
        for n,cell in enumerate(self.cell_locations):
            b = self.button_imgs[n]
            x = cell['x0'] + b.x_padding
            y = cell['y0'] + b.y_padding
            self.bg_img.new_layer(b, x, y, True)
            self.highlight_img.new_layer(b.highlight, x, y, True)
            self.select_img.new_layer(b.select, x, y, True)
    
    def resize_imgs(self):
        '''
        backgrounds:
        NTSC FS: 720x540  -> 720x480
        PAL FS : 768x576  -> 720x576
        NTSC WS: 854x480  -> 720x480
        PAL WS : 1024x576 -> 720x576
        letterboxed buttons:
        NTSC WS: 854x480  -> 720x360 --pad--> 720x480
        PAL WS : 1024x576 -> 720x432 --pad--> 720x576
        '''
        self.bg_img.resize(width=self.storage_width, 
                           height=self.storage_height, 
                           ignore_aspect=True)
        if self.button_imgs is None:
            return
        if self.menu_ar == 16/9:
            if self.dvd_format.lower() == 'ntsc':
                lb_h = 360
            elif self.dvd_format.lower() == 'pal':
                lb_h = 432
            self.highlight_lb_img = Img(self.highlight_img.path)
            self.select_lb_img = Img(self.select_img.path)
            for img in [self.highlight_lb_img, self.select_lb_img]:
                img.resize(width=720, height=lb_h, ignore_aspect=True,
                           remap=True, no_antialias=True, no_dither=True)
                img.pad_to(new_h=self.storage_height)
        for img in [self.highlight_img, self.select_img]:
            img.resize(width=self.storage_width, 
                       height=self.storage_height,
                       ignore_aspect=True, 
                       remap=True, 
                       no_antialias=True, 
                       no_dither=True)
    
    def write(self, out_file_bg=None, out_file_hl=None, out_file_sl=None,
                 out_file_hl_lb=None, out_file_sl_lb=None):
        # TODO: write letterboxed highlight/select images when menu_ar is 16:9
        if out_file_bg is None:
            out_file_bg = self.path_bg_img
        if out_file_hl is None:
            out_file_hl = self.path_hl_img
        if out_file_sl is None:
            out_file_sl = self.path_sl_img
        if out_file_hl_lb is None:
            out_file_hl_lb = self.path_hl_lb_img
        if out_file_sl_lb is None:
            out_file_sl_lb = self.path_sl_lb_img
        self.bg_img.write(out_file=out_file_bg)
        if self.button_imgs is None:
            return
        self.highlight_img.write(out_file=out_file_hl)
        self.select_img.write(out_file=out_file_sl)
        if self.menu_ar == 16/9:
            self.highlight_lb_img.write(out_file=out_file_hl_lb)
            self.select_lb_img.write(out_file=out_file_sl_lb)


class DVDMenu (object):
    def __init__(self, 
                 # input paths
                 menu_imgs, 
                 menu_bg=None,
                 menu_labels=None,
                 # output paths 
                 out_name=None,
                 out_dir=None,
                 tmp_dir=None,
                 # ------bg opts------
                 # padding
                 outer_padding=None, 
                 inner_padding=None,
                 label_padding=None, 
                 # size/shape 
                 menu_ar=16/9,
                 dvd_format='NTSC',
                 # buttons
                 button_border_color=None, 
                 button_border_thickness=None, 
                 button_highlight_color=None, 
                 button_highlight_thickness=None,
                 button_select_color=None,
                 shadow_sigma=None, 
                 shadow_x_offset=None, 
                 shadow_y_offset=None,
                 # labels
                 label_line_height=None, 
                 label_lines=None,
                 # ------menu opts------
                 menu_audio=None
                 ):
         # input paths
        self.menu_imgs = menu_imgs
        self.menu_bg = menu_bg
        self.menu_labels = menu_labels
         # output paths 
        self.out_name = out_name
        self.out_dir = out_dir
        self.tmp_dir = tmp_dir
         # ---------------bg opts --------------------
         # padding
        self.outer_padding = outer_padding
        self.inner_padding = inner_padding
        self.label_padding = label_padding
         # size/shape
        if type(menu_ar) == str:
            ar_w, ar_h = menu_ar.split(':')
            menu_ar = int(ar_w) / int(ar_h)
        self.menu_ar = menu_ar
        self.dvd_format = dvd_format
        # buttons
        self.button_border_color = button_border_color
        self.button_border_thickness = button_border_thickness
        self.button_highlight_color = button_highlight_color
        self.button_highlight_thickness = button_highlight_thickness
        self.button_select_color = button_select_color
        self.shadow_sigma = shadow_sigma
        self.shadow_x_offset = shadow_x_offset
        self.shadow_y_offset = shadow_y_offset
        # labels
        self.label_line_height = label_line_height
        self.label_lines = label_lines
        # menu
        self.menu_audio = menu_audio
        #-----------------
        self.get_out_paths()
        self.get_bg()
        self.convert_to_m2v()
        self.convert_audio()
        self.multiplex_audio()
        self.create_menu_mpg()
    
    def get_out_paths(self):
        paths = utils.get_out_paths(PROG_NAME, self.out_name, self.out_dir,
                                    self.tmp_dir, 150*1024*1024)
        self.out_name, self.out_dir, self.tmp_dir = paths
        self.out_files_dir = os.path.join(self.out_dir, 'files')
        fdir = self.out_files_dir
        out_name = self.out_name
        self.path_menu_lb_mpg = os.path.join(fdir, 
                                             '{}_menu_lb.mpg'.format(out_name))        
        self.path_bg_m2v = os.path.join(fdir, '{}_bg.m2v'.format(out_name))
        self.path_bg_ac3 = os.path.join(fdir, '{}_bg.ac3'.format(out_name))
        self.path_bg_mpg = os.path.join(fdir, '{}_bg.mpg'.format(out_name))
        self.path_menu_mpg = os.path.join(fdir, '{}_menu.mpg'.format(out_name))
        self.path_menu_xml = os.path.join(fdir, '{}_menu.xml'.format(out_name))
        self.path_menu_lb_xml = os.path.join(fdir, 
                                             '{}_menu_lb.xml'.format(out_name))
    def get_bg(self):
        bg_attrs = ['menu_bg',
                    'menu_labels',
                    # output paths 
                    'out_name',
                    'out_dir',
                    'tmp_dir',
                    # padding
                    'outer_padding',
                    'inner_padding',
                    'label_padding',
                    # size/shape 
                    'menu_ar',
                    'dvd_format',
                    # buttons
                    'button_border_color',
                    'button_border_thickness',
                    'button_highlight_color',
                    'button_highlight_thickness',
                    'button_select_color',
                    'shadow_sigma',
                    'shadow_x_offset',
                    'shadow_y_offset',
                    # labels
                    'label_line_height',
                    'label_lines']
        bg_args = {}
        for k in bg_attrs:
            v = getattr(self, k)
            if v is not None:
                bg_args[k] = v
        self.bg = BG(menu_imgs=self.menu_imgs, **bg_args)
    
    def convert_to_m2v(self, frames=360):
        frames = str(frames)
        if self.dvd_format == 'PAL':
            framerate = '25:1'
            pixel_aspect = '59:54'
            fmt = 'p'
        else:
            framerate = '30000:1001'
            pixel_aspect = '10:11'
            fmt = 'n'
        if self.menu_ar == 16/9:
            aspect = '3'
        else:
            aspect = '2'
        p1 = subprocess.Popen(['convert', self.bg.path_bg_img, 'ppm:-'], 
                              stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['ppmtoy4m', '-n', frames, '-F', framerate, 
                               '-A', pixel_aspect, '-I', 'p', '-r', 
                               '-S', '420mpeg2'], 
                              stdin=p1.stdout, stdout=subprocess.PIPE)
        p1.stdout.close()
        p3 = subprocess.Popen(['mpeg2enc', '-n', fmt, '-f', '8', '-b', '5000', 
                               '-a', aspect, '-o', self.path_bg_m2v], 
                              stdin=p2.stdout,stdout=subprocess.PIPE)
        p2.stdout.close()
        output, err = p3.communicate()
        self.frames = frames
    
    def convert_audio(self):
        if self.menu_audio:
            in_file = ['-i', self.menu_audio]
            cmd = ['ffmpeg'] + in_file + ['-ac', '2', '-ar', '48000', 
                   '-b:a', '224000', '-codec:a', 'ac3', '-y', self.path_bg_ac3]
            o = subprocess.check_output(cmd, universal_newlines=True)
            return
        # else make silent audio file for menu
        if self.dvd_format == 'PAL':
            samples = int(self.frames) * 1920
        else:
            samples = int(self.frames) * 1601.6
        samples = math.floor(samples)
        p1 = subprocess.Popen(['dd', 'if=/dev/zero', 'bs=4', 
                               'count={}'.format(samples)], 
                              stdout=subprocess.PIPE)
        p2 = subprocess.Popen(['toolame', '-b', '128', '-s', '48', '/dev/stdin',
                               self.path_bg_ac3], 
                              stdin=p1.stdout)
        p1.stdout.close()
        out, err = p2.communicate()
    
    def multiplex_audio(self):
        cmd = ['mplex', '-f', '8', '-o', self.path_bg_mpg, self.path_bg_m2v,
               self.path_bg_ac3]
        o = subprocess.check_output(cmd, universal_newlines=True)
    
    def create_menu_mpg(self):
        if self.menu_imgs is None:
            self.path_menu_mpg = self.path_bg_mpg
            return
        self.create_menu_xml(self.bg.path_hl_img, 
                             self.bg.path_sl_img, 
                             self.path_menu_xml)
        self.multiplex_buttons(self.path_bg_mpg, 
                               self.path_menu_mpg, 
                               self.path_menu_xml, 
                               '0')
        if self.menu_ar == 16/9:
            self.create_menu_xml(self.bg.path_hl_lb_img, 
                                 self.bg.path_sl_lb_img, 
                                 self.path_menu_lb_xml)
            self.multiplex_buttons(self.path_menu_mpg, 
                                   self.path_menu_lb_mpg, 
                                   self.path_menu_lb_xml, 
                                   '1')
            self.path_menu_mpg = self.path_menu_lb_mpg
            

    def create_menu_xml(self, hl, sl, xml):
        subpictures = etree.Element('subpictures')
        stream = etree.SubElement(subpictures, 'stream')
        spu = etree.SubElement(stream, 'spu')
        spu.set('start', '00:00:00.00')
        #~ spu.set('end', '00:01:30.00')
        spu.set('force', 'yes')
        spu.set('highlight', hl)
        #~ spu.set('select', sl)
        spu.set('autooutline', 'infer')
        spu.set('autoorder', 'rows')
        tree = etree.ElementTree(subpictures)
        tree.write(xml, encoding='UTF-8', pretty_print=True)

    def multiplex_buttons(self, in_mpg, out_mpg, xml, stream):
        e = dict(os.environ)
        if self.dvd_format == 'PAL':
            e['VIDEO_FORMAT'] = 'PAL'
        else:
            e['VIDEO_FORMAT'] = 'NTSC'
        with open(out_mpg, 'w') as f:
            p1 = subprocess.Popen(['cat', in_mpg], 
                                  stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['spumux', '-s', str(stream), xml], 
                                  stdin=p1.stdout, stdout=f, env=e)
            p1.stdout.close()
            out, err = p2.communicate()


class DVD (object):
    def __init__(self, 
                 # input 
                 in_vids=None, 
                 in_dirs=None, 
                 in_srts=None, 
                 menu_imgs=None, 
                 menu_labels=None, 
                 menu_bg=None, 
                 # input options
                 vid_fmts=['mp4', 'avi', 'mkv'],
                 img_fmts=['png', 'jpg', 'bmp', 'gif'],
                 sub_fmts=['srt'],
                 img_names=['poster', 'folder'],
                 one_vid_per_dir=False,
                 label_from_img=False,
                 label_from_dir=True, 
                 strip_label_year=True,
                 no_encode_v=False, 
                 no_encode_a=False, 
                 unstack_vids=None,
                 # output locations
                 out_name=None, 
                 out_dir=None, 
                 tmp_dir=None,
                 # output options
                 no_prompt=False,
                 with_menu=True, 
                 menu_only=False,
                 with_author_dvd=True,
                 #~ dvd_size_bits=37602983936,
                 dvd_size_bytes=4700372992,
                 # dvd options
                 audio_lang='en',
                 with_subs=False, 
                 sub_lang='en', 
                 dvd_format='NTSC', 
                 dvd_ar=None, 
                 vbitrate=None, 
                 abitrate=196608, 
                 two_pass=True,
                 separate_titles=True, 
                 separate_titlesets=False, 
                 ar_threshold=1.38,
                 # menu options
                 menu_ar=None,
                 with_menu_labels=False, 
                 label_line_height=None,
                 label_lines=None,
                 label_padding=None,
                 outer_padding=None,
                 inner_padding=None,
                 menu_audio=None,
                 no_loop_menu=True):
        self.uid = str(id(self))
        # input 
        self.in_vids=in_vids 
        self.in_dirs=in_dirs 
        self.in_srts=in_srts 
        self.menu_imgs=menu_imgs 
        self.menu_labels=menu_labels 
        self.menu_bg=menu_bg 
        # input options
        self.vid_fmts=vid_fmts
        self.img_fmts=img_fmts
        self.sub_fmts=sub_fmts
        self.img_names = img_names
        self.one_vid_per_dir=one_vid_per_dir
        self.label_from_img=label_from_img
        self.label_from_dir=label_from_dir 
        self.strip_label_year=strip_label_year
        self.no_encode_v=no_encode_v 
        self.no_encode_a=no_encode_a 
        self.unstack_vids=unstack_vids
        # output locations
        self.out_name=out_name 
        self.out_dir=out_dir
        self.tmp_dir=tmp_dir
        # output options
        self.no_prompt=no_prompt
        self.with_menu=with_menu 
        self.menu_only=menu_only
        self.with_author_dvd=with_author_dvd
        self.dvd_size_bytes=dvd_size_bytes
        self.dvd_size_bits = dvd_size_bytes * 8
        # dvd options
        self.audio_lang=audio_lang
        self.with_subs=with_subs 
        self.sub_lang=sub_lang 
        self.dvd_format=dvd_format 
        self.dvd_ar=dvd_ar 
        self.vbitrate=vbitrate 
        self.abitrate=abitrate 
        self.two_pass=two_pass
        self.separate_titles=separate_titles 
        self.separate_titlesets=separate_titlesets 
        self.ar_threshold=ar_threshold
        # menu options
        if type(menu_ar) == str:
            ar_w, ar_h = menu_ar.split(':')
            menu_ar = int(ar_w) / int(ar_h)
        self.menu_ar=menu_ar
        self.with_menu_labels=with_menu_labels 
        self.label_line_height=label_line_height
        self.label_lines = label_lines
        self.label_padding = label_padding
        self.outer_padding = outer_padding
        self.inner_padding = inner_padding
        self.menu_audio = menu_audio
        self.no_loop_menu=no_loop_menu
        #-------------------------------
        if self.menu_ar is None:
            self.menu_ar = self.dvd_ar
        self.get_in_vids()
        self.get_menu_imgs()
        self.get_menu_labels()
        self.get_subs()
        self.get_out_paths()
        # get information about input video
        self.get_media_info()
        self.log_output_info()
        self.log_input_info()
        self.log_titlesets()
        self.prompt_input_output()
        self.calculate_vbitrate()
        # make menu
        if self.with_menu or self.menu_only:
            self.get_menu()
        if self.menu_only:
            return
        self.log_menu_info()
        self.prompt_menu()
        # prepare mpeg2 files
        self.encode_video()
        self.create_dvd_xml()
        # author DVD
        if self.with_author_dvd:
            self.author_dvd()
    
    def get_out_paths(self):
        paths = utils.get_out_paths(PROG_NAME, self.out_name, self.out_dir,
                                    self.tmp_dir, self.dvd_size_bytes * 1.2)
        self.out_name, self.out_dir, self.tmp_dir = paths
        
        self.out_dvd_dir = os.path.join(self.out_dir, 'DVD')
        self.out_files_dir = os.path.join(self.out_dir, 'files')
        self.out_dvd_xml = os.path.join(self.out_files_dir, 
                                        '{}_dvd.xml'.format(self.out_name))
        self.out_log = os.path.join(self.out_files_dir, 
                                    '{}.log'.format(self.out_name))
        # make dirs if they don't exist
        for i in [self.out_dvd_dir, self.out_files_dir, self.tmp_dir]:
            if not os.path.exists(i):
                os.makedirs(i)
        
        # check available space
        devices = {}
        dvd_size = self.dvd_size_bytes
        for d,s in zip([self.out_dvd_dir, self.out_files_dir, self.tmp_dir], 
                       [dvd_size, dvd_size*.1, dvd_size]):
            dev = os.stat(d).st_dev
            if devices.get(dev):
                devices[dev] -= s
            else:
                devices[dev] = get_space_available(i) - s
        if min(devices.values()) < 1024*1024:
            raise
        
        logger.addHandler(logging.FileHandler(self.out_log))
    
    def get_in_vids(self):
        if not self.in_vids:
            if self.unstack_vids is None:
                self.unstack_vids = True
            in_vids = []
            if not self.in_dirs:
                raise
            for d in self.in_dirs:
                for fmt in self.vid_fmts:
                    pat = os.path.join(d, '*.{}'.format(fmt))
                    found = sorted(glob.glob(pat))
                    if found:
                        if self.one_vid_per_dir:
                            in_vids.extend(found[:1])
                            break
                        else:
                            in_vids.extend(found)
            self.in_vids = [i for i in in_vids if i is not None]
        else:
            if self.unstack_vids is None:
                self.unstack_vids = False
    
    def get_menu_imgs(self):
        if not self.with_menu:
            self.menu_imgs = [None for i in self.in_vids]
            return
        if not self.menu_imgs:
            self.menu_imgs = []
            for i in self.in_vids:
                img = self.get_matching_file(i, self.img_fmts, 
                                             self.img_names)
                self.menu_imgs.append(img)
    
    def get_menu_labels(self):
        if not self.menu_labels:
            self.menu_labels = []
            # get labels
            if self.label_from_img:
                label_list = self.menu_imgs
            else:
                label_list = self.in_vids
            if self.label_from_dir:
                pt = 0
            else:
                pt = 1
            self.menu_labels = [os.path.splitext(
                                     os.path.basename(os.path.split(i)[pt]))[0]
                                if i is not None else None 
                                for i in label_list]
        else:
            self.with_menu_labels = True
        self.vid_labels = self.menu_labels
        if self.with_menu and self.with_menu_labels:
            if self.strip_label_year:
                pat = r'\s*\([-./\d]{2,12}\)\s*$'
                self.menu_labels = [re.sub(pat, '', i) 
                                    for i in self.menu_labels]
        else:
            self.menu_labels = [None for i in self.in_vids]
    
    def get_subs(self):
        if self.with_subs:
            if not self.in_srts:
                self.in_srts = []
                for i in self.in_vids:
                    s = self.get_matching_file(i, self.sub_fmts)
                    self.in_srts.append(s)
            else:
                self.in_srts = [None for i in self.in_vids]
    
    def get_matching_file(self, vid, fmts, names=[]):
        dirname, basename = os.path.split(vid)
        name, ext = os.path.splitext(basename)
        for n in [name, basename, '{}*'.format(name)] + names:
            search_base = os.path.join(dirname, n)
            for fmt in fmts:
                search_name = '.'.join([search_base, fmt])
                found = sorted(glob.glob(search_name))
                if found:
                    return found[0]
        # if no exact match found and one_vid_per_dir, we still search for 
        # match based only on file extension
        if self.one_vid_per_dir:
            for fmt in fmts:
                found = sorted(glob.glob(os.path.join(dirname, 
                                                      '*.{}'.format(fmt))))
                if found:
                    return found[0]
        return None
    
    def get_media_info(self):
        vids = []
        fmt = ('--output=Video;%Duration%|^|%Width%|^|%Height%|^|'
               '%PixelAspectRatio%|^|%DisplayAspectRatio%')
        for n,i in enumerate(self.in_vids):
            subs = [self.in_srts[n]] if self.in_srts is not None else [None]
            if self.unstack_vids:
                stacked = self.get_stacked_vids(i)
                if self.with_subs:
                    subs = [self.in_srts[n]]
                    addl_subs = [self.get_matching_file(i, ['srt'], [])
                                 for i in stacked[1:]]
                    for sb in addl_subs:
                        if sb not in subs:
                            subs.append(sb)
            else:
                stacked = [i]
                if self.with_subs:
                    subs = [self.in_srts[n]]
            v = {}
            duration = 0
            for path in stacked:
                mi = subprocess.check_output(['mediainfo', fmt, path], 
                                               universal_newlines=True).strip()
                d_ms,w,h,par,dar = mi.split('|^|')
                d_s = int(d_ms) / 1000
                duration += d_s
                width = int(w)
                height = int(h)
                par = float(par)
                dar = float(dar)
                ar = (width/height) * par
                nv = {'ar': ar,
                      'dar': dar,
                      'width': width,
                      'height': height}
                if v:
                    if nv != v:
                        raise
                else:
                    v.update(nv)
            v['in'] = stacked
            v['mpeg'] = ''
            #~ v['srt'] = self.in_srts[n]
            v['srt'] = subs
            v['duration'] = duration
            v['img'] = self.menu_imgs[n]
            v['menu_label'] = self.menu_labels[n]
            v['vid_label'] = self.vid_labels[n]
            vids.append(v)
        self.vids = vids
        self.titlesets = self.split_titlesets()
        self.durations = [i['duration'] for i in vids]
        self.duration_total = sum(self.durations)
    
    def get_stacked_vids(self, vid_path):
        vid_dir, vid_name = os.path.split(vid_path)
        paths = [i for i in os.listdir(vid_dir) if i != vid_name]
        regex = self.get_stacking_regex()
        matches = []
        for r in regex:
            if not matches:
                vm = re.search(r, vid_name, re.I)
                if vm:
                    ve = vm.expand(r'\1\3\4')
                    for p in paths:
                        pm = re.search(r, p, re.I)
                        if pm:
                            pe = pm.expand(r'\1\3\4')
                            if pe == ve:
                                matches.append(os.path.join(vid_dir, p))
        return [vid_path] + matches
    
    def get_stacking_regex(self):
        re_tem = (r'^(.*?)'     # title
                  r'{}'         # volume
                  r'(.*?)'      # ignore
                  r'(\.[^.]+)'  # extension
                  r'$')
        re_tem_labeled_nums = r'({0}*(?:{1}){0}*{2}+)'.format(RE_PARTS_SEP, 
                                                              RE_VOL_PREFIXES, 
                                                              RE_VOL_NUMS)
        re_tem_labeled_letters = r'({0}*(?:{1}){0}*{2})'.format(RE_PARTS_SEP, 
                                                                RE_VOL_PREFIXES,
                                                                RE_VOL_LETTERS)
        re_tem_bare_letters = r'({0}*{1})'.format(RE_PARTS_SEP, RE_VOL_LETTERS)
        re_stacked_labeled_nums = re_tem.format(re_tem_labeled_nums)
        re_stacked_labeled_letters = re_tem.format(re_tem_labeled_letters)
        re_stacked_bare_letters = re_tem.format(re_tem_bare_letters)
        return [re_stacked_labeled_nums, re_stacked_labeled_letters, 
                re_stacked_bare_letters]
    
    def log_output_info(self):
        logs = list(zip(['Name', 'DVD', 'Files', 'tmp'],
                        [self.out_name, self.out_dvd_dir, self.out_files_dir, 
                         self.tmp_dir]))
        log_items(logs, 'Output Paths')

    def log_input_info(self):
        log_items(heading='Video Information', items=[], lines_before=1)
        for n,i in enumerate(self.vids):
            #~ dirs = [i['in'], i['img'], i['srt']]
            dirs = [p for p in i['in']]
            if i['srt']:
                dirs.extend(i['srt'])
            if i['img']:
                dirs.append(i['img'])
            #~ dirs.extend([i['img'], i['srt']])
            dirs = [os.path.dirname(i) for i in dirs if i is not None]
            commonprefix = utils.get_commonprefix(dirs)
            if len(commonprefix) > 1:
                in_dir = commonprefix
                #~ in_vid = os.path.relpath(i['in'], commonprefix)
                in_vids = [os.path.relpath(v, commonprefix) for v in i['in']]
                if i['srt']:
                    in_srt = [os.path.relpath(v, commonprefix) if v else None 
                              for v in i['srt']]
                else:
                    in_srt = None
                if i['img']:
                    in_img = os.path.relpath(i['img'], 
                                             commonprefix) if i['img'] else None
                else:
                    in_img = None
                #~ in_srt = os.path.relpath(i['srt'], commonprefix)
            else:
                in_dir = None
                #~ in_vid = i['in']
                in_vids = [v for v in i['in']]
                in_img = i['img']
                in_srt = i['srt']
            #~ name = os.path.basename(i['in'])
            duration = self.get_duration_string(i['duration'])
            log_data = list(zip(['In file(s)', 'Image', 'Label', 'Subtitle', 
                             'Aspect Ratio', 'Duration'], 
                            [in_vids, in_img, i['menu_label'], in_srt, 
                             '{:.2f}'.format(i['ar']), duration]))
            if in_dir:
                log_data.append(('In Dir', in_dir))
            log_items('#{}: {}:'.format(n+1, i['vid_label']), lines_before=0,
                      sep_pre='-', sep_post='-')
            log_items(log_data, col_width=12, indent=4)# sep_post='-')
    
    def log_titlesets(self):
        log_items(heading='Titlesets', items=[], lines_before=1)
        for n,i in enumerate(self.titlesets):
            ar = i['ar']
            seconds = sum([d['duration'] for d in i['vids']])
            duration = self.get_duration_string(seconds)
            log_data = list(zip(['Aspect Ratio', 'Duration', 'Titles'], 
                                [ar, duration, 
                                 '{} of {}'.format(len(i['vids']),
                                                   len(self.vids))]))
            log_data.append(('Videos', [v['vid_label'] for v in i['vids']]))
            log_items('Titleset #{} of {}'.format(n+1, len(self.titlesets)),
                      lines_before=0, sep_pre='-', sep_post='-')
            log_items(log_data, col_width=12, indent=4)
    
    def log_menu_info(self):
        if self.menu_ar == 16/9:
            ar = '16:9'
        else:
            ar = '4:3'
        log_data = list(zip(['Aspect Ratio', 'Image', 'Video'],
                            [ar, self.menu.bg.path_bg_img, 
                             self.menu.path_menu_mpg]))
        log_items(heading='Menu', items=log_data, lines_before=1)
    
    def prompt_input_output(self):
        if self.no_prompt:
            return
        choices = ['Continue',
                   'Play a video',
                   'List contents of a directory']
        while True:
            resp = user_input.prompt_user_list(choices)
            if resp is False:
                sys.exit()
            elif resp == 0:
                break
            vids = [i['vid_label'] for i in self.vids]
            path = user_input.prompt_user_list(vids, header=choices[resp])
            # TODO: offer choice of files when video is stacked
            path = self.vids[path]['in'][0]
            if resp == 1:
                o = subprocess.check_call([VIDEO_PLAYER, path])
            elif resp == 2:
                o = subprocess.check_output(['ls', '-lhaF', '--color=auto', 
                                             os.path.dirname(path)],
                                            universal_newlines=True)
                print('\n{}\n\n{}'.format(path, o.strip()))
    
    def prompt_menu(self):
        if self.no_prompt:
            return
        choices = ['Continue',
                   'Display Menu Image',
                   'Play Menu Video']
        while True:
            resp = user_input.prompt_user_list(choices)
            if resp is False:
                sys.exit()
            elif resp == 0:
                break
            if resp == 1:
                o = subprocess.check_call([IMAGE_VIEWER, 
                                           self.menu.bg.path_bg_img])
            elif resp == 2:
                o = subprocess.check_call([VIDEO_PLAYER, 
                                           self.menu.path_menu_mpg])
    
    def get_duration_string(self, seconds):
        h,m,s = str(timedelta(seconds=seconds)).split(':')
        duration = '{:02.0f}:{:02.0f}:{:02.0f}'.format(float(h), float(m), 
                                                       float(s))
        return duration
    
    def split_titlesets(self):
        titlesets = [{'ar': 0, 'vids': [] }]
        for n,i in enumerate(self.vids):
            if self.split_titlesets:
                if i['ar'] < self.ar_threshold:
                    ar = '4:3'
                else:
                    ar = '16:9'
            else:
                ar = self.dvd_ar
            if ar == titlesets[-1]['ar']:
                titlesets[-1]['vids'].append(i)
            else:
                titlesets.append({'ar': ar, 'vids': [i] })
        titlesets = [i for i in titlesets if i['vids']]
        # automatically set dvd_ar if unset
        if self.dvd_ar is None:
            ars = [i['ar'] for i in titlesets]
            if '16:9' in ars:
                self.dvd_ar = 16/9
            else:
                self.dvd_ar = 4/3
            if self.menu_ar is None:
                self.menu_ar = self.dvd_ar
        return titlesets
    
    def calculate_vbitrate(self):
        duration = self.duration_total
        abitrate = self.get_audio_bitrate()
        available = self.dvd_size_bits / duration
        available -= available * .05
        v_available = available - abitrate
        
        if not self.vbitrate:
            self.vbitrate = math.floor(v_available)
        else:
            if self.vbitrate > v_available:
                print('WARNING: Not enough space to encode at specified',
                      'audio/video bitrates!')
        
        total_bitrate = self.vbitrate + self.abitrate
        #~ # 9800kbps (dvd max) = 10035200 bits per second
        #~ if total_bitrate > 10035200:
            #~ self.vbitrate = math.floor(10035200 - self.abitrate)
        
        # 9800kbps (dvd max) = 10035200 bits per second
        if total_bitrate > 9000000:
            self.vbitrate = math.floor(9000000 - self.abitrate)
        
        logs = list(zip(['Total Duration', 'Bitrate', 'Video Bitrate', 
                         'Audio Bitrate'], 
                        [str(timedelta(seconds=duration)), 
                         '{:.1f} kbps'.format(total_bitrate / 1024),
                         '{:.1f} kbps'.format(self.vbitrate / 1024),
                         '{:.1f} kbps'.format(self.abitrate / 1024),]))
        log_items(logs, 'DVD Info')
    
    def get_audio_bitrate(self):
        return self.abitrate
    
    def log_dvd_info(self):
        pass
    
    def get_menu(self):
        log_items(heading='Making DVD Menu...', items=False)
        if not self.with_menu_labels:
            self.menu_label_line_height = 0
        menu_args = {}
        menu_attrs = ['label_line_height',
                      'label_lines',
                      'label_padding',
                      'outer_padding',
                      'inner_padding',
                      'menu_audio']
        for k in menu_attrs:
            v = getattr(self, k)
            if v is not None:
                menu_args[k] = v
        self.menu = DVDMenu(self.menu_imgs, 
                            menu_bg=self.menu_bg,
                            menu_labels=self.menu_labels, 
                            out_dir=self.out_dir,
                            out_name=self.out_name,
                            tmp_dir=self.tmp_dir,
                            menu_ar=self.menu_ar,
                            dvd_format=self.dvd_format,
                            **menu_args)

        self.blank_menu = DVDMenu(menu_imgs=None,
                                  out_dir=self.out_dir,
                                  out_name='blank_menu',
                                  tmp_dir=self.tmp_dir,
                                  menu_ar=self.menu_ar,
                                  dvd_format=self.dvd_format)
    
    def encode_video(self):
        # TODO: self.vids[n]['in'] is now a list of paths 
        if self.no_encode_v:
            log_items('Skipping encoding mpeg2 video...')
            for i in self.vids:
                i['mpeg'] = i['in'][0]
            return
        log_items(heading='Encoding mpeg2 video...', items=False)
        if self.dvd_ar == 16/9:
            aspect = '16:9'
        else:
            aspect = '4:3'
        for ts in self.titlesets:
            aspect = ts['ar']
            for v in ts['vids']:
                e = Encoder(v['in'], 
                            out_dir=self.tmp_dir, 
                            vbitrate=self.vbitrate, 
                            abitrate=self.abitrate,
                            two_pass=self.two_pass,
                            aspect=aspect,
                            dvd_format=self.dvd_format,
                            with_subs=self.with_subs, 
                            in_srt=v['srt'][0])
                mpeg = e.encode()
                v['mpeg'] = mpeg
    
    def create_dvd_xml(self):
        log_items(heading='Making dvdauthor xml...', items=False)
        if self.dvd_format == 'PAL':
            fmt = 'pal'
        else:
            fmt = 'ntsc'
        if self.dvd_ar == 16/9:
            dvd_ar = '16:9'
        else:
            dvd_ar = '4:3'
        if self.menu.menu_ar == 16/9:
            menu_ar = '16:9'
        else:
            menu_ar = '4:3'
        
        dvdauthor = etree.Element('dvdauthor', jumppad='on')
        vmgm = etree.SubElement(dvdauthor, 'vmgm')
        # vmgm menu
        if self.menu:
            menus = etree.SubElement(vmgm, 'menus')
            menus_vid = etree.SubElement(menus, 'video', format=fmt, 
                                         aspect=menu_ar)
            if menu_ar == '16:9':
                menus_vid.set('widescreen', 'nopanscan')
                menus_subpicture = etree.SubElement(menus, 'subpicture')
                sub_stream_ws = etree.SubElement(menus_subpicture, 'stream',
                                                 id='0', mode='widescreen') 
                sub_stream_lb = etree.SubElement(menus_subpicture, 'stream',
                                                 id='1', mode='letterbox') 
            menus_pgc = etree.SubElement(menus, 'pgc')
            #~ for n,i in enumerate(self.menu.buttons):
            for n,i in enumerate(self.menu.bg.button_imgs):
                #~ b = etree.SubElement(menus_pgc, 'button', name=i)
                b = etree.SubElement(menus_pgc, 'button')
                b.text = 'jump title {};'.format(n+1)
            menus_vob = etree.SubElement(menus_pgc, 'vob', 
                                         file=self.menu.path_menu_mpg)
            menus_post = etree.SubElement(menus_pgc, 'post')
            if self.no_loop_menu:
                menus_post.text = 'jump title 1;'
            else:
                menus_post.text = 'jump cell 1;'
        # titlesets
        for n,ts in enumerate(self.titlesets):
            titleset = etree.SubElement(dvdauthor, 'titleset')
            blank_menus = etree.SubElement(titleset, 'menus')
            blank_menus_pgc = etree.SubElement(blank_menus, 'pgc')
            blank_menus_pre = etree.SubElement(blank_menus_pgc, 'pre')
            blank_menus_pre.text = 'jump vmgm menu;'
            blank_menus_vob = etree.SubElement(blank_menus_pgc, 'vob', 
                                         file=self.blank_menu.path_menu_mpg)
            blank_menus_post = etree.SubElement(blank_menus_pgc, 'post')
            blank_menus_post.text = 'jump vmgm menu;'
            titles = etree.SubElement(titleset, 'titles')
            titles_vid = etree.SubElement(titles, 'video', format=fmt, 
                                          aspect=ts['ar'])
            titles_audio = etree.SubElement(titles, 'audio', 
                                            lang=self.audio_lang)
            if self.with_subs:
                titles_sub = etree.SubElement(titles, 'subpicture', 
                                              lang=self.sub_lang)
            #~ mpeg_files = [v['mpeg'] for i in ts for v in i['vids']]
            mpeg_files = [v['mpeg'] for v in ts['vids']]
            if n == len(self.titlesets) - 1:
                call_target = 'call vmgm menu;'
            else:
                call_target = 'jump titleset {} title 1;'.format(n+2)
            titles.extend(self.populate_pgcgroup(mpeg_files, 
                                                 self.separate_titles, 
                                                 call_target))
        # write xml to disk
        tree = etree.ElementTree(dvdauthor)
        tree.write(self.out_dvd_xml, encoding='UTF-8', pretty_print=True)
    
    def populate_pgcgroup(self, in_vids, separate_titles, call_target):
        groups = []
        vobs = [etree.Element('vob', file=i) for i in in_vids]
        if separate_titles:
            for n,i in enumerate(vobs):
                pgc = etree.Element('pgc')
                pgc.append(i)
                #~ pgc.extend(i)
                post = etree.SubElement(pgc, 'post')
                if n == len(vobs)-1:
                    post.text = call_target
                else:
                    post.text = 'jump title {};'.format(n+2)
                groups.append(pgc)
        else:
            pgc = etree.Element('pgc')
            pgc.extend(vobs)
            post = etree.SubElement(pgc, 'post')
            post.text = call_target
            groups.append(pgc)
        return groups
    
    def author_dvd(self):
        log_items(heading='Writing DVD to disc...', items=False)
        e = dict(os.environ)
        e['VIDEO_FORMAT'] = self.dvd_format
        cmd = ['dvdauthor', '-x', self.out_dvd_xml, '-o', self.out_dvd_dir]
        o = subprocess.check_output(cmd, env=e, universal_newlines=True)

