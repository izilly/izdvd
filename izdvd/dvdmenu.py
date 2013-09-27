#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

from izdvd.bg import BG
from izdvd import utils
from izdvd import config
import subprocess
import math
from collections import Counter
import os
from lxml import etree


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
        paths = utils.get_out_paths(config.PROG_NAME, self.out_name, 
                                    self.out_dir, self.tmp_dir, 150*1024*1024)
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

