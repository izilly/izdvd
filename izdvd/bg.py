#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

from izdvd.image import Img, CanvasImg, TextImg
from izdvd import utils
from izdvd import user_input
from izdvd import config
import subprocess
import sys
from lxml import etree
import math
from collections import Counter
import os
import logging


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
                 out_log=None,
                 no_prompt=True,
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
                 label_lines=2,
                 mode='bg',
                 no_logging=False,
                 ):
        # input paths
        self.menu_bg = menu_bg
        self.menu_imgs = menu_imgs
        self.menu_labels = menu_labels
        # output paths        
        self.out_name = out_name
        self.out_dir = out_dir
        self.tmp_dir = tmp_dir
        self.out_log = out_log
        self.no_prompt = no_prompt
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
        self.mode = mode
        self.no_logging = no_logging
        #---------
        self.get_out_paths()
        self.log_output_info()
        self.log_input_info()
        self.prompt_input_output()
        self.get_imgs()
        self.get_dims()
        self.make_bg()
        self.resize_bg()
        if self.button_imgs is not None:
            self.calc_cell_ar()
            self.get_grid_size()
            self.resize_buttons()
            self.prepare_buttons()
            self.create_labels()
            self.append_labels()
            self.apply_shadows()
            self.get_cell_locations()
            self.overlay_buttons()
        self.resize_imgs()
        self.write()
        self.get_xml()
    
    def get_out_paths(self):
        paths = utils.get_out_paths(config.PROG_NAME, self.out_name, 
                                    self.out_dir, self.tmp_dir, 50*1024*1024)
        self.out_name, self.out_dir, self.tmp_dir = paths
        
        self.path_bg_img = os.path.join(self.out_dir, 
                                        '{}_background.png'.format(self.out_name))
        self.path_hl_img = os.path.join(self.out_dir, 
                                        '{}_highlight.png'.format(self.out_name))
        self.path_sl_img = os.path.join(self.out_dir, 
                                        '{}_select.png'.format(self.out_name))
        self.path_hl_lb_img = os.path.join(self.out_dir, 
                                  '{}_highlight_letterbox.png'.format(self.out_name))
        self.path_sl_lb_img = os.path.join(self.out_dir, 
                                  '{}_select_letterbox.png'.format(self.out_name))
        self.path_menu_xml = os.path.join(self.out_dir, 
                                          '{}_menu.xml'.format(self.out_name))
        self.path_menu_lb_xml = os.path.join(self.out_dir, 
                                '{}_menu_letterbox.xml'.format(self.out_name))
        if not self.out_log:
            self.out_log = os.path.join(self.out_dir, 
                                        '{}.log'.format(self.out_name))
        if self.no_logging:
            self.out_log = os.devnull
        self.logger = logging.getLogger('{}.bg'.format(config.PROG_NAME))
        self.logger.addHandler(logging.FileHandler(self.out_log))
        self.logger.setLevel(logging.INFO)
    
    def log_input_info(self):
        if not self.no_logging:
            logs = list(zip(['Background', 'Menu Images', 'Menu Labels'],
                            [self.menu_bg, self.menu_imgs, self.menu_labels]))
            utils.log_items(logs, 'Menu Background Information', 
                            logger=self.logger)

    def log_output_info(self):
        if self.mode == 'bg' and not self.no_logging:
            logs = list(zip(['Name', 'Out dir', 'tmp'],
                            [self.out_name, self.out_dir, self.tmp_dir]))
            utils.log_items(logs, 'Output Paths', logger=self.logger)
    
    def prompt_input_output(self):
        if (self.mode in ['bg', 'menu'] and not self.no_logging 
            and not self.no_prompt):
            choices = ['Continue',
                       'Display a menu image']
            while True:
                resp = user_input.prompt_user_list(choices)
                if resp is False:
                    sys.exit()
                elif resp == 0:
                    break
                img = user_input.prompt_user_list(self.menu_imgs, 
                                                  header='Display an image')
                o = subprocess.check_call([config.IMAGE_VIEWER, 
                                           self.menu_imgs[img]],
                                          stderr=subprocess.STDOUT,
                                          stdout=subprocess.DEVNULL)
    
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
            if not self.no_logging:
                utils.log_items(heading='Making menu background canvas...', 
                                items=False, lines_before=1, sep='', 
                                sep_post='-', logger=self.logger)
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
            if not self.no_logging:
                utils.log_items(heading='Resizing menu background...', 
                                items=False, lines_before=1, sep='', sep_post='-',
                                logger=self.logger)
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
        if not self.no_logging:
            utils.log_items(heading=('Calculating the best grid '
                                     'for menu buttons...'),
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        if self.menu_labels:
            has_labels = [i for i in self.menu_labels if i]
        else:
            has_labels = False
        if not has_labels:
            self.menu_labels = None
            self.label_line_height = 0
            self.label_padding = 0
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
        sufficient = [i for i in methods if i['empty'] > -1 and i['area'] > 0]
        if not sufficient:
            print('Not enough space to fit buttons!')
            raise
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
        shadow_padding_x = cols * shadow_padding['x']
        shadow_padding_y = rows * shadow_padding['y']
        border_padding_x = cols * self.button_border_thickness*2
        border_padding_y = rows * self.button_border_thickness*2
        padded_w = bg_w - padding_w - shadow_padding_x - border_padding_x
        padded_h = bg_h - padding_h - label_padding_h - shadow_padding_y - border_padding_y
        col_w = padded_w/cols if padded_w > 0 else 0
        row_h = padded_h/rows if padded_h > 0 else 0
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
        if not self.no_logging:
            utils.log_items(heading='Resizing menu button images...', 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        for i in self.button_imgs:
            if i.ar > self.cell_ar:
                w = self.cell_w
                h = math.floor(self.cell_w / i.ar)
            elif i.ar < self.cell_ar:
                w = math.floor(self.cell_h * i.ar)
                h = self.cell_h
            else:
                w = self.cell_w
                h = self.cell_h
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
        if not self.menu_labels:
            return False
        if not self.no_logging:
            utils.log_items(heading='Making menu label images...', 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
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
        bg_w = self.display_width
        bg_h = self.display_height
        total_cells = list(range(len(self.button_imgs)))
        cells = []
        cell_w = max([i.get_width() for i in self.button_imgs])
        cell_h = max([i.get_height() for i in self.button_imgs])
        padding_y = math.floor((bg_h - cell_h*self.rows) / (self.rows + 1))
        padded_y = cell_h + padding_y
        for r in range(self.rows):
            row_cells = total_cells[len(cells):len(cells)+self.cols]
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
        self.cell_w = cell_w
        self.cell_h = cell_h
    
    def overlay_buttons(self):
        '''Overlays the buttons onto the background image.
        '''
        if self.button_imgs is None:
            return
        self.highlight_img = self.bg_img.new_canvas()
        self.select_img = self.bg_img.new_canvas()
        for n,cell in enumerate(self.cell_locations):
            b = self.button_imgs[n]
            x_padding = math.floor((self.cell_w - b.get_width()) / 2)
            y_padding = math.floor((self.cell_h - b.get_height()) / 2)
            x = cell['x0'] + x_padding
            y = cell['y0'] + y_padding
            self.bg_img.new_layer(b, x, y, layers_method='flatten')
            self.highlight_img.new_layer(b.highlight, 
                                         x + b.x_offset, 
                                         y + b.y_offset, 
                                         True, layers_method='flatten')
            self.select_img.new_layer(b.select, 
                                      x + b.x_offset, 
                                      y + b.y_offset,
                                      True, layers_method='flatten')
    
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
    
    def get_xml(self):
        self.create_menu_xml(self.path_hl_img, 
                             self.path_sl_img, 
                             self.path_menu_xml,
                             mode='normal')
        if self.menu_ar == 16/9:
            self.create_menu_xml(self.path_hl_lb_img, 
                                 self.path_sl_lb_img, 
                                 self.path_menu_lb_xml,
                                 mode='letterboxed')
            

    def create_menu_xml(self, hl, sl, xml, mode='normal'):
        if not self.no_logging:
            utils.log_items(heading=('Writing spumux xml config '
                                     'for menu buttons ({})...'.format(mode)), 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        subpictures = etree.Element('subpictures')
        stream = etree.SubElement(subpictures, 'stream')
        spu = etree.SubElement(stream, 'spu')
        spu.set('start', '00:00:00.00')
        #~ spu.set('end', '00:01:30.00')
        spu.set('force', 'yes')
        spu.set('highlight', hl)
        spu.set('select', sl)
        spu.set('autooutline', 'infer')
        spu.set('autoorder', 'rows')
        tree = etree.ElementTree(subpictures)
        tree.write(xml, encoding='UTF-8', pretty_print=True)
