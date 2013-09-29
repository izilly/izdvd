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
import logging


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
                 out_log=None,
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
                 menu_audio=None,
                 frames=360,
                 mode='menu',
                 no_logging=False,
                 ):
         # input paths
        self.menu_imgs = menu_imgs
        self.menu_bg = menu_bg
        self.menu_labels = menu_labels
         # output paths 
        self.out_name = out_name
        self.out_dir = out_dir
        self.tmp_dir = tmp_dir
        self.out_log = out_log
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
        self.frames = frames
        self.mode = mode
        self.no_logging = no_logging
        #-----------------
        self.get_out_paths()
        self.get_bg()
        self.convert_to_m2v()
        self.convert_audio()
        self.multiplex_audio()
        self.create_menu_mpg()
        self.log_menu_info()
    
    def get_out_paths(self):
        paths = utils.get_out_paths(config.PROG_NAME, self.out_name, 
                                    self.out_dir, self.tmp_dir, 150*1024*1024)
        self.out_name, self.out_dir, self.tmp_dir = paths
        self.out_files_dir = os.path.join(self.out_dir, 'menu-files')
        if not os.path.exists(self.out_files_dir):
            os.makedirs(self.out_files_dir)
        self.path_menu_mpg = os.path.join(self.out_dir, 
                                          '{}_menu.mpg'.format(self.out_name))
        self.path_bg_m2v = os.path.join(self.out_files_dir, 
                                      '{}_menu_video.m2v'.format(self.out_name))
        self.path_bg_ac3 = os.path.join(self.out_files_dir, 
                                      '{}_menu_audio.ac3'.format(self.out_name))
        self.path_bg_mpg = os.path.join(self.out_files_dir, 
                                 '{}_menu_mplexed.mpg'.format(self.out_name))
        self.path_menu_lb_mpg = os.path.join(self.out_files_dir, 
                                  '{}_menu_letterbox.mpg'.format(self.out_name))        
        #~ self.path_menu_xml = os.path.join(self.out_files_dir, 
                                          #~ '{}_menu.xml'.format(self.out_name))
        #~ self.path_menu_lb_xml = os.path.join(self.out_files_dir, 
                                        #~ '{}_menu_lb.xml'.format(self.out_name))
        if not self.out_log:
            self.out_log = os.path.join(self.out_dir, 
                                        '{}.log'.format(self.out_name))
        if self.no_logging:
            self.out_log = os.devnull
        self.logger = logging.getLogger('{}.menu'.format(config.PROG_NAME))
        self.logger.addHandler(logging.FileHandler(self.out_log))
        self.logger.setLevel(logging.INFO)
    
    def log_output_info(self):
        if self.mode == 'menu' and not self.no_logging:
            logs = list(zip(['Name', 'Out Dir', 'Files', 'tmp'],
                            [self.out_name, self.out_dir, self.out_files_dir, 
                             self.tmp_dir]))
            utils.log_items(logs, 'Output Paths', logger=self.logger)
    
    def get_bg(self):
        bg_attrs = ['menu_bg',
                    'menu_labels',
                    # output paths 
                    #~ 'out_name',
                    #~ 'out_dir',
                    #~ 'tmp_dir',
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
        if not self.no_logging:
            utils.log_items(heading='Making menu background...', 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        self.bg = BG(menu_imgs=self.menu_imgs, 
                     out_name=self.out_name,
                     out_dir=self.out_files_dir,
                     tmp_dir=self.tmp_dir,
                     out_log=self.out_log, 
                     no_logging=self.no_logging,
                     mode=self.mode,
                     **bg_args)
    
    def convert_to_m2v(self, frames=None):
        if frames is None:
            frames = self.frames
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
        if not self.no_logging:
            utils.log_items(heading=('Converting menu background '
                                     'to mpeg2 video...'), 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        with open(self.out_log, 'a') as log:
            if self.no_logging:
                log = subprocess.DEVNULL
            p1 = subprocess.Popen(['convert', self.bg.path_bg_img, 'ppm:-'], 
                                  stdout=subprocess.PIPE, 
                                  stderr=log)
            p2 = subprocess.Popen(['ppmtoy4m', '-n', frames, '-F', framerate, 
                                   '-A', pixel_aspect, '-I', 'p', '-r', 
                                   '-S', '420mpeg2'], 
                                  stdin=p1.stdout, stdout=subprocess.PIPE,
                                  stderr=log)
            p1.stdout.close()
            p3 = subprocess.Popen(['mpeg2enc', '-n', fmt, '-f', '8', '-b', '5000', 
                                   '-a', aspect, '-o', self.path_bg_m2v], 
                                  stdin=p2.stdout,stdout=subprocess.PIPE,
                                  stderr=log)
            p2.stdout.close()
            output, err = p3.communicate()
    
    def convert_audio(self):
        if self.menu_audio:
            in_file = ['-i', self.menu_audio]
            cmd = ['ffmpeg'] + in_file + ['-ac', '2', '-ar', '48000', 
                   '-b:a', '224000', '-codec:a', 'ac3', '-y', self.path_bg_ac3]
            if not self.no_logging:
                utils.log_items(heading='Transcoding menu audio to ac3...', 
                                items=False, lines_before=1, sep='', sep_post='-',
                                logger=self.logger)
            with open(self.out_log, 'a') as log:
                if self.no_logging:
                    log = subprocess.DEVNULL
                o = subprocess.check_output(cmd, universal_newlines=True,
                                            stderr=log)
            return
        # else make silent audio file for menu
        if self.dvd_format == 'PAL':
            samples = int(self.frames) * 1920
        else:
            samples = int(self.frames) * 1601.6
        samples = math.floor(samples)
        if not self.no_logging:
            utils.log_items(heading='Creating blank audio for menu...', 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        with open(self.out_log, 'a') as log:
            if self.no_logging:
                log = subprocess.DEVNULL
            p1 = subprocess.Popen(['dd', 'if=/dev/zero', 'bs=4', 
                                   'count={}'.format(samples)], 
                                  stdout=subprocess.PIPE, stderr=log)
            p2 = subprocess.Popen(['toolame', '-b', '128', '-s', '48', '/dev/stdin',
                                   self.path_bg_ac3], 
                                  stdin=p1.stdout, stderr=log, stdout=log)
            p1.stdout.close()
            out, err = p2.communicate()
    
    def multiplex_audio(self):
        cmd = ['mplex', '-f', '8', '-o', self.path_bg_mpg, self.path_bg_m2v,
               self.path_bg_ac3]
        if not self.no_logging:
            utils.log_items(heading='Multiplexing menu audio/video...', 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        with open(self.out_log, 'a') as log:
            if self.no_logging:
                log = subprocess.DEVNULL
            o = subprocess.check_output(cmd, universal_newlines=True,
                                        stderr=log)
    
    def create_menu_mpg(self):
        if self.menu_imgs is None:
            os.rename(self.path_bg_mpg, self.path_menu_mpg)
            #~ self.path_menu_mpg = self.path_bg_mpg
            return
        #~ self.create_menu_xml(self.bg.path_hl_img, 
                             #~ self.bg.path_sl_img, 
                             #~ self.path_menu_xml,
                             #~ mode='normal')
        self.multiplex_buttons(self.path_bg_mpg, 
                               self.path_menu_mpg, 
                               self.bg.path_menu_xml, 
                               '0',
                               mode='normal')
        if self.menu_ar == 16/9:
            #~ self.create_menu_xml(self.bg.path_hl_lb_img, 
                                 #~ self.bg.path_sl_lb_img, 
                                 #~ self.path_menu_lb_xml,
                                 #~ mode='letterboxed')
            self.multiplex_buttons(self.path_menu_mpg, 
                                   self.path_menu_lb_mpg, 
                                   self.bg.path_menu_lb_xml, 
                                   '1',
                                   mode='letterboxed')
            os.remove(self.path_menu_mpg)
            os.rename(self.path_menu_lb_mpg, self.path_menu_mpg)
            #~ self.path_menu_mpg = self.path_menu_lb_mpg
            

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
        #~ spu.set('select', sl)
        spu.set('autooutline', 'infer')
        spu.set('autoorder', 'rows')
        tree = etree.ElementTree(subpictures)
        tree.write(xml, encoding='UTF-8', pretty_print=True)

    def multiplex_buttons(self, in_mpg, out_mpg, xml, stream, mode='normal'):
        e = dict(os.environ)
        if self.dvd_format == 'PAL':
            e['VIDEO_FORMAT'] = 'PAL'
        else:
            e['VIDEO_FORMAT'] = 'NTSC'
        if not self.no_logging:
            utils.log_items(heading=('Multiplexing menu buttons '
                                     'w/ spumux ({})...'.format(mode)), 
                            items=False, lines_before=1, sep='', sep_post='-',
                            logger=self.logger)
        with open(out_mpg, 'w') as f:
            with open(self.out_log, 'a') as log:
                if self.no_logging:
                    log = subprocess.DEVNULL
                p1 = subprocess.Popen(['cat', in_mpg], 
                                      stdout=subprocess.PIPE, stderr=log)
                p2 = subprocess.Popen(['spumux', '-s', str(stream), xml], 
                                      stdin=p1.stdout, stdout=f, stderr=log, 
                                      env=e)
                p1.stdout.close()
                out, err = p2.communicate()
    
    def log_menu_info(self):
        if not self.no_logging:
            if self.menu_ar == 16/9:
                ar = '16:9'
            else:
                ar = '4:3'
            log_data = list(zip(['Aspect Ratio', 'Image', 'Video'],
                                [ar, self.bg.path_bg_img, 
                                 self.path_menu_mpg]))
            utils.log_items(heading='Menu', items=log_data, lines_before=1,
                             logger=self.logger)
    
