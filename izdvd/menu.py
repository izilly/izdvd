#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

from izdvd.image import Img, CanvasImg
import subprocess
import math
from collections import Counter
import argparse


class BG (object):
    def __init__(self, bg_img, button_imgs, button_labels=None, label_size=0,
                 label_lines=2, outer_padding=30, inner_padding=30, 
                 display_ar=None):
        self.bg_img = Img(bg_img)
        self.button_imgs = [Img(i) for i in button_imgs]
        self.button_labels = button_labels
        self.label_size = label_size
        self.outer_padding = outer_padding
        self.inner_padding = inner_padding
        self.width = self.bg_img.width
        self.height = self.bg_img.height
        #~ self.usable_w = self.width - self.outer_padding
        #~ self.usable_h = self.height - self.outer_padding
        self.storage_ar = self.width / self.height
        if display_ar is None:
            self.display_ar = self.storage_ar
        else:
            self.display_ar = display_ar
        self.multiplier = self.storage_ar / self.display_ar
        self.cell_ar = self.calc_cell_ar()
        self.grid = self.get_grid_size()
        self.cols = self.grid['cols']
        self.rows = self.grid['rows']
        self.cell_w = self.grid['cell_w']
        self.cell_h = self.grid['cell_h']
        self.cells = len(self.button_imgs)
        self.resize_buttons()
        self.create_labels()
        self.prepare_buttons()
        self.cell_locations = self.get_cell_locations()
        #~ self.append_labels()
        self.overlay_buttons()
        dd = 1
    
    def calc_cell_ar(self):
        ars = Counter([i.ar for i in self.button_imgs])
        base_ar = ars.most_common()[0][0] * self.multiplier
        return base_ar
    
    def get_grid_size(self):
        '''
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
        bg_w = self.width - self.outer_padding
        bg_h = self.height - self.outer_padding
        bg_ar = bg_w / bg_h
        grid_ratio = bg_ar / self.cell_ar
        buttons = len(self.button_imgs)
        rows = math.sqrt(buttons / grid_ratio)
        cols = math.sqrt(buttons * grid_ratio)
        fcols = math.floor(cols)
        frows = math.floor(rows)
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
            mcols = fcols+i['rounding'][0]
            mrows = frows+i['rounding'][1]
            empty = mcols*mrows - buttons
            i['empty'] = empty
            if empty >= 0:
                area, bw, bh = self.get_cell_size(mcols, mrows, self.cell_ar,
                                                  self.width, self.height)
                i['cols'] = mcols
                i['rows'] = mrows
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
        outer_padding = self.outer_padding * 2
        inner_padding_w = self.inner_padding * (cols - 1)
        inner_padding_h = self.inner_padding * (rows - 1)
        label_padding_h = self.label_size * rows
        padding_w = outer_padding + inner_padding_w
        padding_h = outer_padding + inner_padding_h + label_padding_h
        padded_w = bg_w - padding_w
        padded_h = bg_h - padding_h
        col_w = padded_w / cols
        row_h = padded_h / rows
        cell_w = col_w
        cell_h = cell_w/cell_ar
        if cell_h > row_h:
            cell_h = row_h
            cell_w = cell_h*cell_ar
        # return area, cell_width, cell_height
        return cell_w*cell_h, math.floor(cell_w), math.floor(cell_h)
    
    def prepare_buttons(self):
        for i in self.button_imgs:
            #~ i.resize(self.cell_w, self.cell_h)
            hl = i.new_canvas()
            hl.border('green', 5)
            i.highlight = hl
            sl = i.new_canvas()
            sl.border('red', 5)
            i.select = sl
            i.border('white', 5)
            i.append([self.label_bg])
            i.drop_shadow()
    
    def resize_buttons(self):
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
    
    def get_cell_locations(self):
        cells = self.cells
        cols = self.cols
        rows = self.rows
        cell_w = self.cell_w
        cell_h = self.cell_h + self.label_size
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
        return cells
    
    def create_labels(self):
        if not self.button_labels or not self.label_size > 0:
            return False
        self.label_bg = CanvasImg(self.cell_w, self.label_size, 'red')
    
    def append_labels(self):
        for i in self.button_imgs:
            i.append([self.label_bg])
    
    def overlay_buttons(self):
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
    


