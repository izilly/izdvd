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

PROG_NAME = 'WTA_DVD'
BLANK_MPG = '/home/will/Videos/dvdauthoring/00-menus/blank.mpg'
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
    def __init__(self, bg_img, button_imgs, 
                 button_labels=None, 
                 out_dir=None, out_name=None,
                 border_px=5, border_color='white', 
                 highlight_color='#56B356', select_color='red',
                 label_line_height=0, label_lines=2, 
                 label_padding=5, outer_padding=30, inner_padding=30, 
                 width=None, height=None, display_ar=None):
        self.bg_img = Img(bg_img)
        self.button_imgs = [Img(i) for i in button_imgs]
        self.out_dir = out_dir
        self.out_name = out_name
        self.border_px = border_px
        self.border_color = border_color
        self.highlight_color = highlight_color
        self.select_color = select_color
        self.setup_out_dir()
        self.button_labels = button_labels
        self.label_line_height = label_line_height
        self.label_lines = label_lines
        self.label_padding = label_padding
        self.outer_padding = outer_padding
        self.inner_padding = inner_padding
        if width is None:
            self.width = self.bg_img.width
        else:
            self.width = width
        if height is None:
            self.height = self.bg_img.height
        else:
            self.height = height
        self.bg_img.resize(self.width, self.height, ignore_aspect=True)
        self.storage_ar = self.width / self.height
        if display_ar is None:
            self.display_ar = self.storage_ar
        else:
            self.display_ar = display_ar
        self.multiplier = self.storage_ar / self.display_ar
        self.cells = len(self.button_imgs)
        #
        self.calc_cell_ar()
        self.get_grid_size()
        self.resize_buttons()
        self.prepare_buttons()
        self.create_labels()
        self.append_labels()
        self.apply_shadows()
        self.get_cell_locations()
        self.overlay_buttons()
        dd = 1
    
    def setup_out_dir(self):
        # output directory
        if self.out_dir is None:
            out_dir = os.getcwd()
        else:
            out_dir = self.out_dir
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
        # output name
        if self.out_name is None:
            out_time = datetime.now().strftime('%Y.%m.%d-%H%M%S')
            out_name = 'DVD_menu_{}'.format(out_time)
        else:
            out_name = self.out_name
        # file paths
        self.out_path = os.path.join(out_dir, out_name)
        self.out_dir = out_dir
        self.out_name = out_name
        self.path_bg_img = '{}_bg.png'.format(self.out_path)
        self.path_hl_img = '{}_hl.png'.format(self.out_path)
        self.path_sl_img = '{}_sl.png'.format(self.out_path)
        
        self.path_bg_m2v = '{}_bg.m2v'.format(self.out_path)     # menu-bg.m2v
        self.path_bg_ac3 = '{}_bg.ac3'.format(self.out_path)     # menu_audio.ac3
        self.path_bg_mpg = '{}_bg.mpg'.format(self.out_path)     # menu-bg.mpg
        self.path_menu_mpg = '{}_menu.mpg'.format(self.out_path) # menu.mpg
        self.path_menu_xml = '{}_menu.xml'.format(self.out_path) # menu.xml
        self.path_dvd_xml = '{}_dvd.xml'.format(self.out_path)   # dvd.xml
        #~ self.path_dvd_dir    VIDEO_TS
    
    def calc_cell_ar(self):
        '''Gets the most common aspect ratio of all button images.
        
        Buttons with any other a/r will be padded to fit in a cell 
        with this a/r.
        
        Returns:    aspect ratio (float)
                        (corrected for any difference between storage 
                         and display aspect ratios.)
        '''
        ars = Counter([i.ar for i in self.button_imgs])
        base_ar = ars.most_common()[0][0] * self.multiplier
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
            buttons = gr * rows^2
            buttons / gr = rows^2
            sqrt(buttons / gr) = rows
            
            buttons = cols * (cols/gr)
            buttons = cols^2/gr
            buttons*gr = cols^2
            sqrt(buttons*gr) = cols
        '''
        bg_w = self.width - self.outer_padding*2
        bg_h = self.height - self.outer_padding*2
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
        padded_w = bg_w - padding_w
        padded_h = bg_h - padding_h - label_padding_h
        col_w = padded_w / cols
        row_h = padded_h / rows
        cell_w = col_w
        cell_h = cell_w/cell_ar
        if cell_h > row_h:
            cell_h = row_h
            cell_w = cell_h*cell_ar
        # return area, cell_width, cell_height
        return cell_w*cell_h, math.floor(cell_w), math.floor(cell_h)
    
    def resize_buttons(self):
        '''Resize each button image to fit into the aspect ratio stored in
        self.cell_ar and corrects for any difference between storage and 
        display aspect ratios.
        
        Returns:    None
                        (modifies self.button_imgs)
        '''
        for i in self.button_imgs:
            i.storage_ar = i.ar * self.multiplier
            if i.storage_ar > self.cell_ar:
                w = self.cell_w
                h = math.floor(self.cell_w / self.cell_ar)
                i.x_padding = 0
                i.y_padding = math.floor((self.cell_h - h) / 2)
            elif i.storage_ar < self.cell_ar:
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
            #~ i.resize(self.cell_w, self.cell_h)
            hl = i.new_canvas()
            hl.border(1, shave=True)
            hl.border(self.border_px*2, self.highlight_color)
            i.highlight = hl
            sl = i.new_canvas()
            sl.border(1, shave=True)
            sl.border(self.border_px*2, self.select_color)
            i.select = sl
            i.border(self.border_px, self.border_color)
            #~ i.append([self.label_bg], padding=self.label_padding)
            #~ i.drop_shadow()
    
    def create_labels(self):
        '''Create images for each label to be placed alongside the button 
        images.
        '''
        if not self.button_labels or not self.label_line_height > 0:
            self.label_imgs = None
            return False
        button_w = max([i.get_width() for i in self.button_imgs])
        labels = []
        for i in self.button_labels:
            img = TextImg(i, line_height=self.label_line_height, 
                                  max_width=button_w, 
                                  max_lines=self.label_lines,
                                  strokewidth=4)
            labels.append(img)
        height = max([i.get_height() for i in labels])
        for i in labels:
            if i.get_height() < height:
                i.pad_to(new_w=i.get_width(), new_h=height)
        self.label_imgs = labels
        #~ self.label_bg = CanvasImg(button_w, self.label_line_height, 'red')
    
    def append_labels(self):
        '''Appends label images to button images to create a new image 
        containing both.
        '''
        if self.label_imgs:
            for n,img in enumerate(self.button_imgs):
                img.append([self.label_imgs[n]], padding=self.label_padding)
    
    def apply_shadows(self):
        for i in self.button_imgs:
            i.drop_shadow()
    
    def get_cell_locations(self):
        '''Get the coordinates at which to place each button
        
        Returns:    cell locations (dict)
                        x0: left edge
                        y0: top edge
                        x1: right edge
                        y1: bottom edge
        '''
        cells = self.cells
        cols = self.cols
        rows = self.rows
        cell_w = self.cell_w
        cell_h = self.cell_h + self.label_line_height + self.label_padding
        bg_w = self.width
        bg_h = self.height
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
        hl = self.bg_img.new_canvas()
        sl = self.bg_img.new_canvas()
        for i,cell in enumerate(self.cell_locations):
            b = self.button_imgs[i]
            x = cell['x0'] + b.x_padding
            y = cell['y0'] + b.y_padding
            self.bg_img.new_layer(b, x, y, True)
            hl.new_layer(b.highlight, x, y, True)
            sl.new_layer(b.select, x, y, True)
        self.highlight_img = hl
        self.select_img = sl
    
    def write_bg(self, out_file_bg=None, out_file_hl=None, out_file_sl=None):
        if out_file_bg is None:
            out_file_bg = self.path_bg_img
        if out_file_hl is None:
            out_file_hl = self.path_hl_img
        if out_file_sl is None:
            out_file_sl = self.path_sl_img
        self.bg_img.write(out_file=out_file_bg)
        self.highlight_img.write(out_file=out_file_hl)
        self.select_img.write(out_file=out_file_sl)


class DVDMenu (object):
    def __init__(self, bg_img, button_imgs, 
                 button_labels=None, 
                 out_dir=None, out_name=None,
                 label_line_height=0, label_lines=2, 
                 label_padding=5, outer_padding=80, inner_padding=40, 
                 dvd_format='NTSC', dvd_menu_ar=4/3, dvd_menu_audio=None):
        #~ width = 720
        if dvd_menu_ar == 4/3:
            width = 640
        else:
            width = 854
        if dvd_format == 'NTSC':
            height = 480
        elif self.dvd_format == 'PAL':
            height = 576
        display_ar = width / height
        self.out_dir = out_dir
        self.out_name = out_name
        self.dvd_format = dvd_format
        self.dvd_menu_ar = dvd_menu_ar
        self.dvd_menu_audio = dvd_menu_audio
        self.bg = BG(bg_img, button_imgs, 
                     button_labels=button_labels,
                     out_dir=out_dir, out_name=out_name,
                     label_line_height=label_line_height, 
                     label_lines=label_lines, 
                     label_padding=label_padding, 
                     outer_padding=outer_padding, 
                     inner_padding=inner_padding, 
                     width=width, height=height, 
                     #~ display_ar=dvd_menu_ar)
                     display_ar=display_ar)
        self.setup_out_dir()
        self.bg.bg_img.resize(720, height, ignore_aspect=True)
        self.bg.highlight_img.resize(720, height, ignore_aspect=True,
                                     no_antialias=True, no_dither=True, 
                                     remap=True)
        self.bg.select_img.resize(720, height, ignore_aspect=True, 
                                  no_antialias=True, no_dither=True, 
                                     remap=True)
        self.bg.write_bg(out_file_bg=self.path_bg_img, 
                      out_file_hl=self.path_hl_img,
                      out_file_sl=self.path_sl_img)
        if self.dvd_menu_ar == 16/9:
            self.bg.highlight_lb_img = Img(self.path_hl_img)
            self.bg.select_lb_img = Img(self.path_sl_img)
            
            self.bg.highlight_lb_img.resize(720, 360, ignore_aspect=True, 
                                            no_antialias=True, no_dither=True, 
                                         remap=True)
            self.bg.select_lb_img.resize(720, 360, ignore_aspect=True, 
                                         no_antialias=True, no_dither=True, 
                                         remap=True)
            self.bg.highlight_lb_img.pad_to(new_h=480)
            self.bg.select_lb_img.pad_to(new_h=480)
            
            self.bg.highlight_lb_img.write(out_file=self.path_hl_lb_img)
            self.bg.select_lb_img.write(out_file=self.path_sl_lb_img)
        
        self.convert_to_m2v()
        self.convert_audio()
        self.multiplex_audio()
        #~ self.multiplex_buttons()
        self.create_menu_mpg()
    
    def setup_out_dir(self):
        # output directory
        if self.out_dir is None:
            out_dir = os.getcwd()
        else:
            out_dir = self.out_dir
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
        # output name
        if self.out_name is None:
            out_time = datetime.now().strftime('%Y.%m.%d-%H%M%S')
            out_name = 'DVD_menu_{}'.format(out_time)
        else:
            out_name = self.out_name
        # file paths
        self.out_path = os.path.join(out_dir, out_name)
        self.out_dir = out_dir
        self.out_name = out_name
        self.path_bg_img = '{}_bg.png'.format(self.out_path)
        self.path_hl_img = '{}_hl.png'.format(self.out_path)
        self.path_sl_img = '{}_sl.png'.format(self.out_path)
        if self.dvd_menu_ar == 16/9:
            self.path_hl_lb_img = '{}_hl_lb.png'.format(self.out_path)
            self.path_sl_lb_img = '{}_sl_lb.png'.format(self.out_path)
            self.path_menu_lb_mpg = '{}_menu_lb.mpg'.format(self.out_path)
            self.path_menu_lb_xml = '{}_menu_lb.xml'.format(self.out_path)
        self.path_bg_m2v = '{}_bg.m2v'.format(self.out_path)     # menu-bg.m2v
        self.path_bg_ac3 = '{}_bg.ac3'.format(self.out_path)     # menu_audio.ac3
        self.path_bg_mpg = '{}_bg.mpg'.format(self.out_path)     # menu-bg.mpg
        self.path_menu_mpg = '{}_menu.mpg'.format(self.out_path) # menu.mpg
        self.path_menu_xml = '{}_menu.xml'.format(self.out_path) # menu.xml
        self.path_dvd_xml = '{}_dvd.xml'.format(self.out_path)   # dvd.xml
        #~ self.path_dvd_dir    VIDEO_TS

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
        if self.dvd_menu_ar == 16/9:
            aspect = '3'
        else:
            aspect = '2'
        p1 = subprocess.Popen(['convert', self.path_bg_img, 'ppm:-'], 
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
        # dd if=/dev/zero bs=4 count=number-of-samples | toolame -b 128 -s 48 /dev/stdin output.m2a
        if self.dvd_menu_audio:
            in_file = ['-i', self.dvd_menu_audio]
            cmd = ['ffmpeg'] + in_file + ['-ac', '2', '-ar', '48000', 
                   '-b:a', '224000', '-codec:a', 'ac3', '-y', self.path_bg_ac3]
            o = subprocess.check_output(cmd, universal_newlines=True)
            return
        # else make silent audio file for menu
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
    
    #def create_menu_mpg(self):
        ##~ self.buttons = []
        #subpictures = etree.Element('subpictures')
        #stream = etree.SubElement(subpictures, 'stream')
        #spu = etree.SubElement(stream, 'spu')
        #spu.set('start', '00:00:00.0')
        #spu.set('highlight', self.path_hl_img)
        #spu.set('select', self.path_sl_img)
        #spu.set('autooutline', 'infer')
        #spu.set('autoorder', 'rows')
        #for n,i in enumerate(self.bg.cell_locations):
            #b_name = 'b{}'.format(n)
            #self.buttons.append(b_name)
            ##~ b = etree.SubElement(spu, 'button')
            ##~ b.set('name', b_name)
            ##~ x0 = i['x0'] - self.bg.border_px
            ##~ x1 = i['x1'] + self.bg.border_px
            ##~ y0 = i['y0'] - self.bg.border_px
            ##~ y1 = i['y1'] + self.bg.border_px
            ##~ if y0 % 2:
                ##~ y0 -= 1
            ##~ if y1 % 2:
                ##~ y1 += 1
            ##~ b.set('x0', str(x0))
            ##~ b.set('x1', str(x1))
            ##~ b.set('y0', str(y0))
            ##~ b.set('y1', str(y1))
        #tree = etree.ElementTree(subpictures)
        #tree.write(self.path_menu_xml, encoding='UTF-8', pretty_print=True)
        #e = dict(os.environ)
        #e['VIDEO_FORMAT'] = 'NTSC'
        #with open(self.path_menu_mpg, 'w') as f:
            #p1 = subprocess.Popen(['cat', self.path_bg_mpg], 
                                  #stdout=subprocess.PIPE)
            #p2 = subprocess.Popen(['spumux', self.path_menu_xml], 
                                  #stdin=p1.stdout, stdout=f, env=e)
            #p1.stdout.close()
            #out, err = p2.communicate()

    def create_menu_mpg(self):
        #~ self.buttons = []
        self.create_menu_xml(self.path_hl_img, self.path_sl_img, 
                             self.path_menu_xml)
        self.multiplex_buttons(self.path_bg_mpg, self.path_menu_mpg,
                               self.path_menu_xml, '0')
        if self.dvd_menu_ar == 16/9:
            self.create_menu_xml(self.path_hl_lb_img, self.path_sl_lb_img, 
                                 self.path_menu_lb_xml)
            self.multiplex_buttons(self.path_menu_mpg, self.path_menu_lb_mpg,
                                   self.path_menu_lb_xml, '1')
            self.path_menu_mpg = self.path_menu_lb_mpg
            

    def create_menu_xml(self, hl, sl, xml):
        subpictures = etree.Element('subpictures')
        stream = etree.SubElement(subpictures, 'stream')
        spu = etree.SubElement(stream, 'spu')
        spu.set('start', '00:00:00.00')
        spu.set('end', '00:01:30.00')
        spu.set('force', 'yes')
        spu.set('highlight', hl)
        #~ spu.set('select', sl)
        spu.set('autooutline', 'infer')
        spu.set('autoorder', 'rows')
        tree = etree.ElementTree(subpictures)
        tree.write(xml, encoding='UTF-8', pretty_print=True)

    def multiplex_buttons(self, in_mpg, out_mpg, xml, stream):
        e = dict(os.environ)
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
                 in_vids=None, in_dirs=None, in_parent=None, one_dir=False,
                 in_srts=None, with_subs=False, sub_lang='en', audio_lang='en',
                 with_menu=True, with_menu_labels=True, label_from_img=False,
                 label_from_dir=True, strip_label_year=True,
                 menu_bg=None, menu_imgs=None, menu_labels=None,
                 menu_label_line_height=18,
                 out_name=None, 
                 out_dvd_dir=None, out_files_dir=None, tmp_dir=None,
                 dvd_format='NTSC', dvd_ar=None, dvd_menu_ar=None,
                 vbitrate=None, abitrate=196608, two_pass=True,
                 no_encode_v=False, no_encode_a=False, 
                 dvd_size_bits=37602983936,
                 separate_titles=True, 
                 separate_titlesets=False, ar_threshold=1.38,
                 no_loop_menu=True):
        self.uid = str(id(self))
        self.in_parent = in_parent
        self.one_dir = one_dir
        self.with_subs = with_subs
        self.sub_lang = sub_lang
        self.audio_lang = audio_lang
        self.with_menu = with_menu
        self.with_menu_labels = with_menu_labels
        self.label_from_img = label_from_img
        self.label_from_dir = label_from_dir
        self.strip_label_year = strip_label_year
        self.menu_label_line_height = menu_label_line_height
        self.dvd_format = dvd_format
        self.dvd_ar = dvd_ar
        if dvd_menu_ar is None:
            self.dvd_menu_ar = dvd_ar
        else:
            self.dvd_menu_ar = dvd_menu_ar
        self.vbitrate = vbitrate
        self.abitrate = abitrate
        self.two_pass = two_pass
        self.no_encode_v = no_encode_v
        self.no_encode_a = no_encode_a
        self.dvd_size_bits = dvd_size_bits
        self.dvd_size_bytes = dvd_size_bits / 8
        self.separate_titles = separate_titles
        self.separate_titlesets = separate_titlesets
        self.ar_threshold = ar_threshold
        self.no_loop_menu = no_loop_menu
        # setup paths
        self.get_out_files(out_name, out_dvd_dir, out_files_dir, tmp_dir)
        self.get_in_files(in_vids, in_dirs, menu_imgs, menu_labels, menu_bg,
                          in_srts)
        # get information about the video files
        self.get_media_info()
        self.log_output_info()
        self.log_input_info()
        self.log_titlesets()
        self.calculate_vbitrate()
        # make menu
        self.get_menu()
        # prepare mpeg2 files
        self.encode_video()
        self.create_dvd_xml()
        # author DVD
        self.author_dvd()
    
    def get_out_files(self, out_name, out_dvd_dir, out_files_dir, tmp_dir):
        home = os.path.expandvars('$HOME')
        tmp = tempfile.gettempdir()
        home_free = get_space_available(home)
        tmp_free = get_space_available(tmp)
        # name
        if not out_name:
            out_time = datetime.now().strftime('%Y.%m.%d-%H%M%S')
            out_name = '{}_{}'.format(PROG_NAME, out_time)
        # tmp_dir
        if not tmp_dir:
            if tmp_free > self.dvd_size_bytes * 1.05:
                tmp_dir = os.path.join(tmp, PROG_NAME, self.uid)
            else:
                tmp_dir = os.path.join(home, PROG_NAME, self.uid)
        # dvd_dir
        if not out_dvd_dir:
            out_dvd_dir = os.path.join(home, PROG_NAME, self.uid, 'DVD')
        # files_dir
        if not out_files_dir:
            out_files_dir = os.path.join(tmp, PROG_NAME, self.uid, 'Menu')
        # make dirs if not present
        for i in [out_dvd_dir, out_files_dir, tmp_dir]:
            if not os.path.exists(i):
                os.makedirs(i)
        # check available space
        fs = {}
        dvd_size = self.dvd_size_bytes
        for d,s in zip([out_dvd_dir, out_files_dir, tmp_dir], 
                       [dvd_size, dvd_size*.1, dvd_size]):
            dev = os.stat(d).st_dev
            if fs.get(dev):
                fs[dev] -= s
            else:
                fs[dev] = get_space_available(i) - s
        if min(fs.values()) < 1024*1024:
            raise
        # dvdauthor xml file
        out_dvd_xml = os.path.join(out_files_dir, '{}_dvd.xml'.format(out_name))
        out_log = os.path.join(out_files_dir, '{}.log'.format(out_name))
        logger.addHandler(logging.FileHandler(out_log))

        
        self.out_name = out_name
        self.out_dvd_dir = out_dvd_dir
        self.out_files_dir = out_files_dir
        self.tmp_dir = tmp_dir
        self.out_dvd_xml = out_dvd_xml
        self.out_log = out_log
    
    def get_in_files(self, in_vids, in_dirs,
                     menu_imgs, menu_labels, menu_bg,
                     in_srts):
        vid_fmts = ['*.mp4', '*.avi', '*.mkv']
        img_fmts = ['*.png', '*.jpg', '*.bmp', '*.gif']
        sub_fmts = ['*.srt']
        if not in_vids:
            in_vids = []
            if not in_dirs:
                if not self.in_parent:
                    raise
                if self.one_dir:
                    in_dirs = [self.in_parent]
                else:
                    in_dirs = sorted([os.path.join(self.in_parent, i) 
                                for i in os.listdir(self.in_parent) if
                                os.path.isdir(os.path.join(self.in_parent, i))])
            for d in in_dirs:
                for pat in vid_fmts:
                    found = sorted(glob.glob(os.path.join(d, pat)))
                    if found:
                        if not self.one_dir:
                            in_vids.extend(found[:1])
                            break
                        else:
                            in_vids.extend(found)
            in_vids = [i for i in in_vids if i is not None]
        
        if self.with_menu:
            if not menu_bg:
                bg = CanvasImg(720, 480, 'gray')
                menu_bg = bg.path
            if not menu_imgs:
                menu_imgs = []
                for i in in_vids:
                    img = self.get_matching_file(i, 
                                                 ['png', 'jpg', 'bmp', 'gif'], 
                                                 ['poster', 'folder'])
                    menu_imgs.append(img)
            
        if not menu_labels:
            menu_labels = []
            # get labels
            if self.label_from_img:
                label_list = menu_imgs
            else:
                label_list = in_vids
            if self.label_from_dir:
                pt = 0
            else:
                pt = 1
            
            menu_labels = [os.path.splitext(
                             os.path.basename(os.path.split(i)[pt]))[0]
                      if i is not None else None 
                      for i in label_list]
            vid_labels = menu_labels
            if self.with_menu and self.with_menu_labels:
                if self.strip_label_year:
                    pat = r'\s*\([-./\d]{2,12}\)\s*$'
                    menu_labels = [re.sub(pat, '', i) for i in menu_labels]
            else:
                menu_labels = None
                    
                
        if self.with_subs:
            if not in_srts:
                in_srts = []
                for i in in_vids:
                    s = self.get_matching_file(i, ['srt'], [])
                    in_srts.append(s)
        
        self.in_vids = in_vids
        self.in_dirs = in_dirs
        self.menu_imgs = menu_imgs
        self.menu_labels = menu_labels
        self.vid_labels = vid_labels
        self.menu_bg = menu_bg
        self.in_srts = in_srts
        
        for i in ['menu_imgs', 'menu_labels', 'in_srts']:
            if getattr(self, i) is None:
                setattr(self, i, [None for v in self.in_vids])
    
    def get_matching_file(self, vid, fmts, names):
        dirname, basename = os.path.split(vid)
        name, ext = os.path.splitext(basename)
        for n in [name, basename] + names:
            search_base = os.path.join(dirname, n)
            for fmt in fmts:
                search_name = '.'.join([search_base, fmt])
                if os.path.exists(search_name):
                    return search_name
        if self.one_dir:
            return None
        for fmt in fmts:
            found = sorted(glob.glob(os.path.join(dirname, '*.{}'.format(fmt))))
            if found:
                return found[0]
        return None
    
    def get_media_info(self):
        vids = []
        durations = []
        for n,i in enumerate(self.in_vids):
            fmt = ('--output=Video;%Duration%|^|%Width%|^|%Height%|^|'
                   '%PixelAspectRatio%|^|%DisplayAspectRatio%')
            mi = subprocess.check_output(['mediainfo', fmt, i], 
                                           universal_newlines=True).strip()
            d_ms,w,h,par,dar = mi.split('|^|')
            d_s = int(d_ms) / 1000
            w = int(w)
            h = int(h)
            par = float(par)
            dar = float(dar)
            ar = (w/h) * par
            v = {'in': i, 
                 'srt': self.in_srts[n],
                 'ar': ar,
                 'dar': dar,
                 'duration': d_s,
                 'mpeg': '',
                 'img': self.menu_imgs[n],
                 'menu_label': self.menu_labels[n],
                 'vid_label': self.vid_labels[n], }
            vids.append(v)
            durations.append(d_s)
        self.vids = vids
        self.titlesets = self.split_titlesets()
        #~ self.titlesets = [i for i in titlesets if i['vids']]
        self.durations = durations
        self.duration_total = sum(durations)

    def log_output_info(self):
        logs = list(zip(['Name', 'DVD', 'Files', 'tmp'],
                        [self.out_name, self.out_dvd_dir, self.out_files_dir, 
                         self.tmp_dir]))
        log_items(logs, 'Output Paths')

    def log_input_info(self):
        log_items(heading='Video Information', items=[], lines_before=1)
        for n,i in enumerate(self.vids):
            dirs = [i['in'], i['img'], i['srt']]
            dirs = [i for i in dirs if i is not None]
            commonprefix = utils.get_commonprefix(dirs)
            if len(commonprefix) > 1:
                in_dir = commonprefix
                in_vid = os.path.relpath(i['in'], commonprefix)
                in_img = os.path.relpath(i['img'], commonprefix)
                in_srt = os.path.relpath(i['srt'], commonprefix)
            else:
                in_dir = None
                in_vid = i['in']
                in_img = i['img']
                in_srt = i['srt']
            name = os.path.basename(i['in'])
            duration = self.get_duration_string(i['duration'])
            log_data = list(zip(['In file', 'Image', 'Label', 'Subtitle', 
                             'Aspect Ratio', 'Duration'], 
                            [in_vid, in_img, i['menu_label'], in_srt, 
                             '{:.2f}'.format(i['ar']), duration]))
            if in_dir:
                log_data.append(('In Dir', in_dir))
            log_items('#{}: {}:'.format(n+1, i['vid_label']), lines_before=1,
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
                      lines_before=1, sep_pre='-', sep_post='-')
            log_items(log_data, col_width=12, indent=4)
    
    def prompt_user(self):
        choices = ['1: Continue',
                             '2: Play a video',
                             '3: List contents of a directory']
        responses = [n+1 for n,i in enumerate(choices)]
        prompt = 'Make a selection: [{}]'.format('/'.join([str(i) for i in responses]))
        #~ prompt = 'Make a selection: [{}]'.format('/'.join(responses))
        prompt = '\n'.join(choices + [prompt])
        r = input('Continue? [Y/n]: ')
    
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
            if self.dvd_menu_ar is None:
                self.dvd_menu_ar = self.dvd_ar
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
        # 9800kbps (dvd max) = 10035200 bits per second
        if total_bitrate > 10035200:
            self.vbitrate = math.floor(10035200 - self.abitrate)
        
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
        self.menu = DVDMenu(self.menu_bg, self.menu_imgs, 
                            button_labels=self.menu_labels, 
                            label_line_height=self.menu_label_line_height,
                            out_dir=self.out_files_dir,
                            out_name=self.out_name,
                            dvd_menu_ar=self.dvd_menu_ar)
    
    def encode_video(self):
        if self.no_encode_v:
            log_items('Skipping encoding mpeg2 video...')
            for i in self.vids:
                i['mpeg'] = i['in']
            return
        log_items(heading='Encoding mpeg2 video...', items=False)
        if self.dvd_ar == 16/9:
            aspect = '16:9'
        else:
            aspect = '4:3'
        for ts in self.titlesets:
            aspect = ts['ar']
            for v in ts['vids']:
                e = Encoder(v['in'], out_dir=self.tmp_dir, 
                                    vbitrate=self.vbitrate, 
                                    abitrate=self.abitrate,
                                    two_pass=self.two_pass,
                                    aspect=aspect,
                                    with_subs=self.with_subs, 
                                    in_srt=v['srt'])
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
        if self.menu.dvd_menu_ar == 16/9:
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
                                         file=BLANK_MPG)
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
        e['VIDEO_FORMAT'] = 'NTSC'
        cmd = ['dvdauthor', '-x', self.out_dvd_xml, '-o', self.out_dvd_dir]
        o = subprocess.check_output(cmd, env=e, universal_newlines=True)



