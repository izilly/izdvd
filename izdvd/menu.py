#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

from izdvd.image import Img, CanvasImg, TextImg
import subprocess
import math
from collections import Counter
import argparse


class BG (object):
    def __init__(self, bg_img, button_imgs, 
                 button_labels=None, label_line_height=0, label_lines=2, 
                 label_padding=5, outer_padding=30, inner_padding=30, 
                 display_ar=None):
        self.bg_img = Img(bg_img)
        self.button_imgs = [Img(i) for i in button_imgs]
        self.button_labels = button_labels
        self.label_line_height = label_line_height
        self.label_lines = label_lines
        self.label_padding = label_padding
        self.outer_padding = outer_padding
        self.inner_padding = inner_padding
        self.width = self.bg_img.width
        self.height = self.bg_img.height
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
        
        print('Best:')
        for i in best_methods:
            print('  {}: {}x{}  {:.0f}x{:.0f}  ({} empty)'.format(i['name'], i['cols'], 
                                                   i['rows'], i['bw'], i['bh'],
                                                    i['empty'] ))
        print('')
        if tied_methods:
            print('Tied:')
            for i in tied_methods:
                print('  {}: {}x{}  {:.0f}x{:.0f}  ({} empty)'.format(i['name'], i['cols'], 
                                                       i['rows'], i['bw'], i['bh'],
                                                        i['empty'] ))
            print('')
        if other_methods:
            print('Other:')
            for i in other_methods:
                print('  {}: {}x{}  {:.0f}x{:.0f}  ({} empty)'.format(i['name'], i['cols'], 
                                                       i['rows'], i['bw'], i['bh'],
                                                        i['empty'] ))
            print('')
    
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
            hl.border('green', 5)
            i.highlight = hl
            sl = i.new_canvas()
            sl.border('red', 5)
            i.select = sl
            i.border('white', 5)
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
    


