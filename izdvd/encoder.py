#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

import os
import argparse
import subprocess
import re
import math
from lxml import etree

class Error(Exception):
    def __init__(self, message):
        self.message = message

class Encoder (object):
    def __init__(self, 
                 in_file=None, 
                 in_srt=None, 
                 out_file=None, 
                 out_dir=None, 
                 aspect='16:9', 
                 dvd_format='NTSC',
                 vbitrate=1000000, 
                 abitrate=96000, 
                 two_pass=True, 
                 dry_run=False, 
                 get_args=False, 
                 with_subs=False):
        self.in_file = in_file
        self.in_srt= in_srt
        self.out_file = out_file
        self.out_dir = out_dir
        self.aspect = aspect
        self.dvd_format = dvd_format
        self.vbitrate = vbitrate
        self.abitrate = abitrate
        self.two_pass = two_pass
        self.dry_run = dry_run
        self.with_subs = with_subs
        if in_srt:
            self.with_subs = True
        ######
        if get_args:
            self.get_options()
        self.setup_in_files()
        self.setup_out_files()
        if self.in_files_cat:
            self.create_cat_file()
        self.get_size()
        self.calculate_scaling()
        self.calculate_padding()
        if self.with_subs:
            self.write_srt()
            self.create_subs_xml()
        self.passnum = '1'
    
    def setup_in_files(self):
        self.in_files_cat = None
        if type(self.in_file) is list:
            if len(self.in_file) > 1:
                self.in_files_cat = self.in_file
            self.in_file = self.in_file[0]
    
    def create_cat_file(self):
        lines = '\n'.join(["file '{}'".format(i) for i in self.in_files_cat])
        with open(self.cat_file, 'w') as f:
            f.write(lines)
    
    def setup_out_files(self):
        in_filename = os.path.basename(self.in_file)
        in_name, in_ext = os.path.splitext(in_filename)
        # out_file and out_dir
        if self.out_file:
            out_dir, out_filename = os.path.split(self.out_file)
            self.out_dir = os.path.abspath(out_dir)
            self.out_name, out_ext = os.path.splitext(out_filename)
            if out_ext.lower() not in ['.mpg', '.mpeg']:
                self.out_file = '{}.mpg'.format(self.out_file)
                self.out_name = os.path.splitext(self.out_file)[0]
        else:
            self.out_name = in_name
            if not self.out_dir:
                self.out_dir = os.getcwd()
            self.out_file = os.path.join(self.out_dir, 
                                         '{}.mpg'.format(self.out_name))
        # other output
        self.log_file = os.path.join(self.out_dir, 
                                     '{}.log'.format(self.out_name))
        self.subs_srt = os.path.join(self.out_dir, 
                                     '{}.srt'.format(self.out_name))
        self.subs_xml = os.path.join(self.out_dir, 
                                     '{}.subs.xml'.format(self.out_name))
        self.cat_file = os.path.join(self.out_dir, 
                                     '{}.cat.txt'.format(self.out_name))
        # make out_dir if it doesn't exist
        if not os.path.exists(self.out_dir):
            os.makedirs(self.out_dir)
    
    def get_options(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('in_file', help='input video file')
        parser.add_argument("--aspect", choices=['16:9', '4:3'], default='16:9')
        parser.add_argument("-vb", "--video-bitrate", default='1000000')
        parser.add_argument('-ab', "--audio-bitrate", default='96000')
        #~ parser.add_argument('-s', "--scale", default=False)
        parser.add_argument('-d', "--dry-run", action='store_true')
        args = parser.parse_args()
        self.in_file = args.in_file
        self.aspect = args.aspect
        self.vbitrate = args.video_bitrate
        self.abitrate = args.audio_bitrate
        self.dry_run = args.dry_run
        #~ self.scale = args.scale
        print('\nInput file: {}\n'.format(args.in_file))
    
    def get_size(self):
        info = subprocess.check_output(['mediainfo', self.in_file], 
                                       universal_newlines=True).splitlines()
        for l in info:
            if l.startswith('Width '):
                width = re.search(r':\s*(\d+)', l).group(1)
                self.width = int(width)
            elif l.startswith('Height '):
                height = re.search(r':\s*(\d+)', l).group(1)
                self.height = int(height)
            elif l.startswith('Display aspect ratio '):
                dar_mi = l.partition(':')[2].strip()
                if ':' in dar_mi:
                    x,y = dar_mi.split(':')
                    dar = float(x) / float(y)
                else:
                    dar = float(dar_mi)
                self.dar = dar
    
    def calculate_scaling(self):
        if self.aspect == '4:3':
            self.display_ar = 4/3
        elif self.aspect == '16:9':
            self.display_ar = 16/9
        
        if self.dvd_format.lower() == 'pal':
            self.storage_width = 720
            self.storage_height = 576
            self.fps = 25
            self.fps_str = '25'
            self.ffmpeg_target = 'pal-dvd'
            if self.aspect == '4:3':
                self.display_width = 768
                self.display_height = 576
            elif self.aspect == '16:9':
                self.display_width = 1024
                self.display_height = 576
            else:
                raise
        elif self.dvd_format.lower() == 'ntsc':
            self.storage_width = 720
            self.storage_height = 480
            self.fps = 30000/1001
            self.fps_str = '29.97'
            self.ffmpeg_target = 'ntsc-dvd'
            if self.aspect == '4:3':
                self.display_width = 640
                self.display_height = 480
            elif self.aspect == '16:9':
                self.display_width = 854                
                self.display_height = 480
            else:
                raise
        else:
            raise
        if self.dar >= self.display_ar:
            self.scale_w = self.storage_width
            self.scale_h = math.floor(self.display_width/self.dar)
        else:
            self.scale_h = self.storage_height
            self.scale_w = math.floor((self.display_height*self.dar) *
                                      (self.storage_width / self.display_width))
    
    def calculate_padding(self):
        self.pad_x = math.floor((self.storage_width - self.scale_w) / 2)
        self.pad_y = math.floor((self.storage_height - self.scale_h) / 2)
        self.scale = 'scale={}:{}'.format(self.scale_w, self.scale_h)
        self.pad = 'pad={}:{}:{}:{}:0x000000'.format(self.storage_width,
                                                     self.storage_height,
                                                     self.pad_x, 
                                                     self.pad_y)

        self.vf = '{},{}'.format(self.scale, self.pad)
        print('-filter:v {}'.format(self.vf))
    
    def write_srt(self):
        if self.in_srt:
            with open(self.in_srt, 'rb') as f:
                b = f.read()
            t = None
            for enc in ['utf-8', 'iso8859-1']:
                try:
                    t = b.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue
        else:
            t= None
        if not t:
            t = '1\n00:00:00,000 --> 00:01:00,000\nSubs'
        with open(self.subs_srt, 'w') as f:
            f.write(t)
    
    def create_subs_xml(self):
        subpictures = etree.Element('subpictures')
        stream = etree.SubElement(subpictures, 'stream')
        textsub = etree.SubElement(stream, 'textsub')
        textsub.set('filename', self.subs_srt)
        textsub.set('characterset', 'UTF-8')
        textsub.set('fontsize', '28.0')
        textsub.set('font', 'arial.ttf')
        textsub.set('fill-color', 'rgba(220, 220, 220, 255)')
        textsub.set('outline-color', 'rgba(35, 35, 35, 175)')
        textsub.set('outline-thickness', '2.0')
        textsub.set('shadow-offset', '2, 2')
        textsub.set('shadow-color', "rgba(35, 35, 35, 175)")
        textsub.set('horizontal-alignment', "center")
        textsub.set('vertical-alignment', "bottom")
        textsub.set('subtitle-fps', self.fps_str)
        textsub.set('movie-fps', self.fps_str)
        textsub.set('aspect', self.aspect)
        textsub.set('force', 'no')
        tree = etree.ElementTree(subpictures)
        tree.write(self.subs_xml, encoding='UTF-8', pretty_print=True)
    
    def build_cmd(self, passnum, args_only=False):
        passnum = str(passnum)
        enc_opts = [{'-target': self.ffmpeg_target},
                        {'-aspect': self.aspect},
                        {'-filter:v': self.vf},
                        {'-s': '{}x{}'.format(self.storage_width, 
                                              self.storage_height)},
                        {'-b:v': self.vbitrate},
                        {'-sn': None},
                        #~ {'-g': '12'},
                        #~ {'-bf': '2'},
                        {'-strict': '1'},
                        #~ {'-threads': '4'},
                        #~ {'-trellis': '1'},
                        #~ {'-mbd': '2'},
                        {'-b:a': self.abitrate},
                        {'-acodec': 'ac3'},
                        {'-ac': '2'}]
        if not args_only:
            args = ['ffmpeg']
            if self.in_files_cat:
                args.extend(['-f', 'concat', '-i', self.cat_file])
            else:
                args.extend(['-i', self.in_file])
        else:
            args = []
        [args.extend([str(k), str(v)]) if v is not None else args.extend([str(k)]) 
         for i in enc_opts for (k,v) in i.items()]
        
        if self.two_pass:
            args.extend(['-pass', passnum, '-passlogfile', self.log_file])
        return args
    
    def encode(self):
        if self.two_pass:
            first_pass = self.build_cmd(1) + ['-y', '/dev/null']
            print('First pass: \n{}\n'.format(' '.join(first_pass)))
            if not self.dry_run:
                subprocess.check_call(first_pass)
        
        final_pass = self.build_cmd(2)
        if self.dry_run:
            print('\n{}\n\nSecond pass: \n{}\n'.format('='*78 , 
                                                       ' '.join(final_pass)))
            return None
        
        if self.with_subs:
            e = dict(os.environ)
            e['VIDEO_FORMAT'] = self.dvd_format
            fp = final_pass+['-']
            spu = ['spumux', '-s0', self.subs_xml]
            cmd_str = '{} | {}'.format(' '.join(fp), ' '.join(spu))
            print('\n{}\n\nSecond pass: \n{}\n'.format('='*78 , cmd_str))
            with open(self.out_file, 'w') as f:
                p1 = subprocess.Popen(final_pass+['-'], 
                                      stdout=subprocess.PIPE)
                p2 = subprocess.Popen(['spumux', '-s0', self.subs_xml], 
                                      stdin=p1.stdout, stdout=f, env=e)
                p1.stdout.close()
                out,err = p2.communicate()
        else:
            print('\n{}\n\nSecond pass: \n{}\n'.format('='*78 , 
                                                       ' '.join(final_pass+[self.out_file])))
            subprocess.check_call(final_pass+[self.out_file])
        return self.out_file
                
        
def main():
    enc = Encoder(get_args=True)
    enc.encode()
    return 0

if __name__ == '__main__':
	main()

