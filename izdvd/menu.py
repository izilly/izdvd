#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

from izdvd.image import Img, CanvasImg, TextImg
from izdvd.encoder import Encoder
import tempfile
import subprocess
import math
from collections import Counter
import argparse
from datetime import datetime
import os
from lxml import etree
import glob
import re

PROG_NAME = 'WTA_DVD'

def get_space_available(path):
    s = os.statvfs(path)
    return s.f_frsize * s.f_bavail

class BG (object):
    def __init__(self, bg_img, button_imgs, 
                 button_labels=None, 
                 out_dir=None, out_name=None,
                 border_px=5, border_color='white', 
                 highlight_color='green', select_color='red',
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
            hl.border(self.highlight_color, self.border_px)
            i.highlight = hl
            sl = i.new_canvas()
            sl.border(self.select_color, self.border_px)
            i.select = sl
            i.border(self.border_color, self.border_px)
            #~ i.append([self.label_bg], padding=self.label_padding)
            #~ i.drop_shadow()
    
    def create_labels(self):
        '''Create images for each label to be placed alongside the button 
        images.
        '''
        if not self.button_labels or not self.label_line_height > 0:
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
                 label_padding=5, outer_padding=30, inner_padding=30, 
                 dvd_format='NTSC', dvd_menu_ar=4/3, dvd_menu_audio=None):
        width = 720
        if dvd_format == 'NTSC':
            height = 480
        elif self.dvd_format == 'PAL':
            height = 576
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
                     display_ar=dvd_menu_ar)
        self.setup_out_dir()
        self.bg.write_bg(out_file_bg=self.path_bg_img, 
                      out_file_hl=self.path_hl_img,
                      out_file_sl=self.path_sl_img)
        self.convert_to_m2v()
        self.convert_audio()
        self.multiplex_audio()
        self.multiplex_buttons()
    
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

    def convert_to_m2v(self, frames=3000):
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
    
    def multiplex_buttons(self):
        self.buttons = []
        subpictures = etree.Element('subpictures')
        stream = etree.SubElement(subpictures, 'stream')
        spu = etree.SubElement(stream, 'spu')
        spu.set('start', '00:00:00.0')
        spu.set('highlight', self.path_hl_img)
        spu.set('select', self.path_sl_img)
        for n,i in enumerate(self.bg.cell_locations):
            b_name = 'b{}'.format(n)
            self.buttons.append(b_name)
            b = etree.SubElement(spu, 'button')
            b.set('name', b_name)
            x0 = i['x0'] - self.bg.border_px
            x1 = i['x1'] + self.bg.border_px
            y0 = i['y0'] - self.bg.border_px
            y1 = i['y1'] + self.bg.border_px
            if y0 % 2:
                y0 -= 1
            if y1 % 2:
                y1 += 1
            b.set('x0', str(x0))
            b.set('x1', str(x1))
            b.set('y0', str(y0))
            b.set('y1', str(y1))
        tree = etree.ElementTree(subpictures)
        tree.write(self.path_menu_xml, encoding='UTF-8', pretty_print=True)
        e = dict(os.environ)
        e['VIDEO_FORMAT'] = 'NTSC'
        with open(self.path_menu_mpg, 'w') as f:
            p1 = subprocess.Popen(['cat', self.path_bg_mpg], 
                                  stdout=subprocess.PIPE)
            p2 = subprocess.Popen(['spumux', self.path_menu_xml], 
                                  stdin=p1.stdout, stdout=f, env=e)
            p1.stdout.close()
            out, err = p2.communicate()




class DVD (object):
    def __init__(self, 
                 in_vids=None, in_dirs=None, in_parent=None, one_dir=False,
                 with_menu=True, with_menu_labels=True, label_from_img=False,
                 label_from_dir=True, strip_label_year=True,
                 menu_bg=None, menu_imgs=None, menu_labels=None,
                 #~ menu=None, 
                 out_name=None, 
                 out_dvd_dir=None, out_menu_dir=None, tmp_dir=None,
                 dvd_format='NTSC', dvd_ar=16/9,
                 vbitrate=None, abitrate=192000, 
                 no_encode_v=False, no_encode_a=False, 
                 dvd_size_bits=37602983936,
                 separate_titles=False):
        self.uid = str(id(self))
        self.in_vids = in_vids
        self.in_dirs = in_dirs
        self.in_parent = in_parent
        self.one_dir = one_dir
        self.with_menu = with_menu
        self.with_menu_labels = with_menu_labels
        self.label_from_img = label_from_img
        self.label_from_dir = label_from_dir
        self.strip_label_year = strip_label_year
        self.menu_bg = menu_bg
        self.menu_imgs = menu_imgs
        self.menu_labels = menu_labels
        self.out_name = out_name
        self.out_dvd_dir = out_dvd_dir
        self.out_menu_dir = out_menu_dir
        self.tmp_dir = tmp_dir
        self.dvd_format = dvd_format
        self.dvd_ar = dvd_ar
        self.vbitrate = vbitrate
        self.abitrate = abitrate
        self.no_encode_v = no_encode_v
        self.no_encode_a = no_encode_a
        self.dvd_size_bits = dvd_size_bits
        self.dvd_size_bytes = dvd_size_bits / 8
        self.separate_titles = separate_titles
        # setup paths
        self.get_in_files(in_vids, in_dirs, in_parent, one_dir,
                          menu_bg, menu_imgs, menu_labels, 
                          with_menu, with_menu_labels, label_from_img,
                          label_from_dir, strip_label_year)
        self.get_out_files(out_name, out_dvd_dir, out_menu_dir, tmp_dir)
        self.get_menu()
        # prepare mpeg2 files
        self.calculate_vbitrate()
        self.encode_video()
        # setup dvdauthor config
        self.create_dvd_xml()
        # author DVD
        self.author_dvd()
    
    def get_in_files(self, in_vids, in_dirs, in_parent, one_dir,
                     menu_bg, menu_imgs, menu_labels, 
                     with_menu, with_menu_labels, label_from_img, 
                     label_from_dir, strip_label_year):
        #~ vids = []
        #~ imgs = []
        #~ labels = []
        vid_fmts = ['*.mp4', '*.avi', '*.mkv']
        img_fmts = ['*.png', '*.jpg', '*.bmp', '*.gif']
        if not in_vids:
            in_vids = []
            if not in_dirs:
                if not in_parent:
                    raise
                if one_dir:
                    in_dirs = [in_parent]
                else:
                    in_dirs = sorted([os.path.join(in_parent, i) 
                                   for i in os.listdir(in_parent)
                                   if os.path.isdir(os.path.join(in_parent, i))])
            for d in in_dirs:
                for pat in vid_fmts:
                    found = sorted(glob.glob(os.path.join(d, pat)))
                    if found:
                        if not one_dir:
                            in_vids.extend(found[:1])
                            break
                        else:
                            in_vids.extend(found)
            in_vids = [i for i in in_vids if i is not None]
        
        if with_menu:
            if not menu_bg:
                bg = CanvasImg(720, 480, 'gray')
                self.menu_bg = bg.path
            if not menu_imgs:
                menu_imgs = []
                #~ imgs = [self.get_img(i) for i in vids]
                for i in in_vids:
                    img = self.get_img(i, one_dir)
                    menu_imgs.append(img)
            
            if with_menu_labels:
                if not menu_labels:
                    menu_labels = []
                    # get labels
                    if label_from_img:
                        label_list = menu_imgs
                    else:
                        label_list = in_vids
                    if label_from_dir:
                        pt = 0
                    else:
                        pt = 1
                    
                    menu_labels = [os.path.splitext(
                                     os.path.basename(os.path.split(i)[pt]))[0]
                              if i is not None else None 
                              for i in label_list]
                    if strip_label_year:
                        menu_labels = [re.sub(r'\s*\([-./\d]{2,12}\)\s*$', '', i)
                                  for i in menu_labels]
        self.in_vids = in_vids
        self.menu_imgs = menu_imgs
        self.menu_labels = menu_labels
    
    def get_img(self, vid, one_dir):
        img_fmts = ['png', 'jpg', 'bmp', 'gif']
        img_names = ['poster', 'folder']
        dirname, basename = os.path.split(vid)
        name, ext = os.path.splitext(basename)
        for n in [name, basename] + img_names:
            img_base = os.path.join(dirname, n)
            for fmt in img_fmts:
                img = '.'.join([img_base, fmt])
                if os.path.exists(img):
                    return img
        if one_dir:
            return None
        for fmt in img_fmts:
            found = sorted(glob.glob(os.path.join(dirname, '*.{}'.format(fmt))))
            if found:
                return found[0]
        return None
    
    def get_out_files(self, out_name, out_dvd_dir, out_menu_dir, tmp_dir):
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
        # menu_dir
        if not out_menu_dir:
            out_menu_dir = os.path.join(tmp, PROG_NAME, self.uid, 'Menu')
        # make dirs if not present
        for i in [out_dvd_dir, out_menu_dir, tmp_dir]:
            if not os.path.exists(i):
                os.makedirs(i)
        # check available space
        fs = {}
        dvd_size = self.dvd_size_bytes
        for d,s in zip([out_dvd_dir, out_menu_dir, tmp_dir], 
                       [dvd_size, dvd_size*.1, dvd_size]):
            dev = os.stat(d).st_dev
            if fs.get(dev):
                fs[dev] -= s
            else:
                fs[dev] = get_space_available(i) - s
        if min(fs.values()) < 1024*1024:
            raise
        # dvdauthor xml file
        out_dvd_xml = os.path.join(tmp_dir, '{}_dvd.xml'.format(out_name))
        
        self.out_name = out_name
        self.out_dvd_dir = out_dvd_dir
        self.out_menu_dir = out_menu_dir
        self.tmp_dir = tmp_dir
        self.out_dvd_xml = out_dvd_xml
    
    def calculate_vbitrate(self):
        duration = self.get_duration()
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
    
    def get_duration(self):
        durations = []
        for i in self.in_vids:
            d_ms = subprocess.check_output(['mediainfo', 
                                            '--output=General;%Duration%',
                                            i], 
                                           universal_newlines=True).strip()
            d_s = int(d_ms) / 1000
            durations.append(d_s)
        seconds = sum(durations)
        return seconds
    
    def get_audio_bitrate(self):
        return self.abitrate
    
    def encode_video(self):
        if self.no_encode_v:
            self.mpeg_files = [i for i in self.in_vids]
            return
        if self.dvd_ar == 16/9:
            aspect = '16:9'
        else:
            aspect = '4:3'
        self.mpeg_files = []
        for i in self.in_vids:
            e = Encoder(i, out_dir=self.tmp_dir, 
                                vbitrate=self.vbitrate, abitrate=self.abitrate, 
                                aspect=aspect)
            encoded = e.encode()
            self.mpeg_files.append(encoded)
    
    def get_menu(self):
        self.menu = DVDMenu(self.menu_bg, self.menu_imgs, 
                            button_labels=self.menu_labels, 
                            label_line_height=18,
                            out_dir=self.out_menu_dir,
                            out_name=self.out_name)
    
    def create_dvd_xml(self):
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
        
        dvdauthor = etree.Element('dvdauthor')
        vmgm = etree.SubElement(dvdauthor, 'vmgm')
        fpc = etree.SubElement(vmgm, 'fpc')
        fpc.text = 'jump titleset 1 menu;'
        titleset = etree.SubElement(dvdauthor, 'titleset')
        if self.menu:
            menus = etree.SubElement(titleset, 'menus')
            menus_vid = etree.SubElement(menus, 'video', format=fmt, 
                                         aspect=menu_ar)
            menus_pgc = etree.SubElement(menus, 'pgc')
            for n,i in enumerate(self.menu.buttons):
                b = etree.SubElement(menus_pgc, 'button', name=i)
                b.text = 'jump title 1 chapter {};'.format(n+1)
            menus_vob = etree.SubElement(menus_pgc, 'vob', 
                                         file=self.menu.path_menu_mpg)
            menus_post = etree.SubElement(menus_pgc, 'post')
            menus_post.text = 'jump cell 1;'
        titles = etree.SubElement(titleset, 'titles')
        titles_vid = etree.SubElement(titles, 'video', format=fmt, aspect=dvd_ar)
        if self.separate_titles:
            for n,i in enumerate(self.mpeg_files):
                pgc = etree.SubElement(titles, 'pgc')
                v = etree.SubElement(pgc, 'vob', file=i)
                post = etree.SubElement(pgc, 'post')
                if n == len(self.mpeg_files)-1:
                    post.text = 'call menu;'
                else:
                    post.text = 'jump title {};'.format(n+2)
        else:
            titles_pgc = etree.SubElement(titles, 'pgc')
            for i in self.mpeg_files:
                v = etree.SubElement(titles_pgc, 'vob', file=i)
            titles_post = etree.SubElement(titles_pgc, 'post')
            titles_post.text = 'call menu;'
        tree = etree.ElementTree(dvdauthor)
        tree.write(self.out_dvd_xml, encoding='UTF-8', pretty_print=True)
    
    def author_dvd(self):
        e = dict(os.environ)
        e['VIDEO_FORMAT'] = 'NTSC'
        cmd = ['dvdauthor', '-x', self.out_dvd_xml, '-o', self.out_dvd_dir]
        o = subprocess.check_output(cmd, env=e, universal_newlines=True)

