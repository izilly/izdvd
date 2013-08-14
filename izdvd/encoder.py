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

class Error(Exception):
    def __init__(self, message):
        self.message = message

class Encoder (object):
    def __init__(self, in_file=None, out_file=None, out_dir=None, 
                 aspect='16:9', vbitrate=1000000, abitrate=96000, 
                 two_pass=True, dry_run=False, get_args=False):
        self.in_file = in_file
        self.out_file = out_file
        self.out_dir = out_dir
        self.aspect = aspect
        self.vbitrate = vbitrate
        self.abitrate = abitrate
        self.two_pass = two_pass
        self.dry_run = dry_run
        if get_args:
            self.get_options()
        self.setup_out_files()
        #~ self.cwd = os.getcwd()
        #~ self.in_filename = os.path.basename(self.in_file)
        #~ self.log_file = os.path.join(self.cwd, self.in_filename+'.log')
        #~ self.out_file = os.path.join(self.cwd, self.in_filename+'.mpg')
#        self.log_file = self.in_file+'.log'
#        self.out_file = self.in_file+'.mpg'
        self.get_size()
        self.calculate_scaling()
        self.calculate_padding()
        self.passnum = '1'
        #~ self.encode()
    
    def setup_out_files(self):
        self.cwd = os.getcwd()
        self.in_filename = os.path.basename(self.in_file)
        if self.out_file is None:
            if self.out_dir is None:
                self.out_dir = self.cwd
            self.log_file = os.path.join(self.out_dir, self.in_filename+'.log')
            self.out_file = os.path.join(self.out_dir, self.in_filename+'.mpg')
        else:
            self.out_dir = os.path.abspath(os.path.split(self.out_file)[0])
            self.log_file = os.path.splitext(self.out_file)[0] + '.log'
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
        mediainfo = subprocess.check_output(['mediainfo', self.in_file], universal_newlines=True).splitlines()
        for l in mediainfo:
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
                
                #~ dar_mi = re.search(r':\s*(\d+.*)', l)
                #~ dar_mi = re.search(r':\s*([0-9.]+):([0-9.]+)', l)
                #~ dar_w = float(dar_mi.group(1))
                #~ dar_h = float(dar_mi.group(2))
                #~ dar = float(dar_w / dar_h)
                #~ self.dar = dar
        #~ print('DAR info: {} x {}'.format(self.width, self.height))
#        if not self.is_square_dar():
#            self.height_actual = self.height
#            self.height = self.width / self.dar
#            print('non-square DAR!')
#            print('DAR:{} h:{} '.format(self.dar, self.height))
                
#    def is_square_dar(self):
#        ar = self.width / self.height
#        if abs( ar - self.dar ) > .07:
#            #~ print('w:{} h:{} '.format(self.width, self.height))
#            return False
    
    def check_valid_dvd(self):
        if self.height <= 480 and self.width <= 720:
            if self.height > 470 or self.width > 710:
                if abs(self.dar - (16/9)) < .04:
                    w = self.width * (854/720)
                    h = self.height
                    ar = w/h
                    if abs(ar-self.dar) < .04:
                        self.no_scale = True
                        return True
                    else:
                        return False
    
    def calculate_scaling(self):
        self.ar = self.width / self.height
        if self.aspect == '4:3':
            display_width = 640
            display_ar = 4/3
        else:
            display_width = 854
            display_ar = 16/9
        if self.check_valid_dvd():
            self.scale_w = self.width
            self.scale_h = self.height
        elif self.dar >= display_ar:
            self.scale_w = 720
            self.scale_h = math.floor(display_width/self.dar)
        else:
            self.scale_h = 480
            self.scale_w = math.floor((480*self.dar)/(display_width/720))
    
    def calculate_padding(self):
        self.pad_x = math.floor((720-self.scale_w)/2)
        self.pad_y = math.floor((480-self.scale_h)/2)
        self.scale = 'scale={}:{}'.format(self.scale_w, self.scale_h)
        self.pad = 'pad=720:480:{}:{}:0x000000'.format(self.pad_x, self.pad_y)
        self.vf = '{},{}'.format(self.scale, self.pad)
        print('WTA calculated -vf: {}'.format(self.vf))

    
    def ccalculate_padding(self):
        if self.scale:
            self.scale_w, self.scale_h = self.scale.split(':')
            self.scale_w = int(self.scale_w)
            self.scale_h = int(self.scale_h)
            print('user scaling:', self.scale_w, self.scale_h)
        else:
            if self.check_valid_dvd():
                pass
                
            # try first to scale height based on 854px width (which is 720px in DVD)
             # and pad the top/bottom to fill 480px
            self.scale_w = 720
            self.scale_h = math.floor(( self.height * 854 ) / self.width)
            # if calculated height doesn't fit in 480px, then scale width based on
             # 480px height and pad left/right to fill 854px/720px
            print('initial padding: {} x {}'.format(self.scale_w, self.scale_h))
            if self.scale_h > 480:
                self.scale_h = 480
                scale_w_square = ( self.width * 480 ) / self.height
                # now convert to rectangular pixel size
                scale_w_dvd = scale_w_square * ( 720/854 )
                self.scale_w = math.floor(scale_w_dvd)
                if self.scale_w > 720:
                    raise Error('Error: could not calculate a valid DVD resolution')
                if self.scale_w % 2 != 0:
                    self.scale_w -= 1
                print('720w padding: {} x {}'.format(self.scale_w, self.scale_h))
            else:
                if self.scale_h % 2 != 0:
                    self.scale_h -= 1
                print('480h padding: {} x {}'.format(self.scale_w, self.scale_h))
        
        self.pad_x = 0
        self.pad_y = math.floor( ( 480 - self.scale_h ) / 2 )
        if self.pad_y % 2 != 0:
            self.pad_y -= 1
        self.scale = 'scale={}:{}'.format(self.scale_w, self.scale_h)
        self.pad = 'pad=720:480:{}:{}:0x000000'.format(self.pad_x, self.pad_y)
        self.vf = '{},{}'.format(self.scale, self.pad)
        print('WTA calculated -vf: {}'.format(self.vf))
    
    def build_cmd(self, passnum):
        passnum = str(passnum)
        #~ enc_opts = [{'-i': self.in_file},
                        #~ {'-vf': self.vf},
                        #~ {'-target': 'ntsc-dvd'},
                        #~ {'-acodec': 'ac3'},
                        #~ {'-sn': None},
                        #~ {'-g': '12'},
                        #~ {'-bf': '2'},
                        #~ {'-strict': '1'},
                        #~ {'-ac': '2'},
                        #~ {'-s': '720x480'},
                        #~ {'-threads': '4'},
                        #~ {'-trellis': '1'},
                        #~ {'-mbd': '2'},
                        #~ {'-b:v': self.vbitrate},
                        #~ {'-b:a': self.abitrate},
                        #~ {'-aspect': self.aspect},
                        #~ {'-pass': passnum},
                        #~ {'-passlogfile': self.log_file}]
        #~ enc_opts = [{'-i': self.in_file},
                        #~ {'-f': 'dvd'},
                        #~ {'-target': 'ntsc-dvd'},
                        #~ {'-aspect': self.aspect},
                        #~ {'-vf': self.vf},
                        #~ {'-s': '720x480'},
                        #~ {'-b:v': self.vbitrate},
                        #~ {'-b:a': self.abitrate},
                        #~ {'-acodec': 'ac3'},
                        #~ {'-ac': '2'},
                        #~ {'-pass': passnum},
                        #~ {'-passlogfile': self.log_file}]
        #~ enc_opts = [{'-i': self.in_file},
                        #~ {'-f': 'dvd'},
                        #~ {'-target': 'ntsc-dvd'},
                        #~ {'-aspect': self.aspect},
                        #~ {'-vf': self.vf},
                        #~ {'-s': '720x480'},
                        #~ {'-b:v': self.vbitrate},
                        #~ {'-b:a': self.abitrate},
                        #~ {'-acodec': 'ac3'},
                        #~ {'-ac': '2'}]
        enc_opts = [{'-i': self.in_file},
                        {'-f': 'dvd'},
                        {'-target': 'ntsc-dvd'},
                        #~ {'-target': 'film-dvd'},
                        {'-aspect': self.aspect},
                        {'-vf': self.vf},
                        {'-s': '720x480'},
                        {'-b:v': self.vbitrate},
                        {'-sn': None},
                        {'-g': '12'},
                        {'-bf': '2'},
                        {'-strict': '1'},
                        {'-threads': '4'},
                        {'-trellis': '1'},
                        {'-mbd': '2'},
                        {'-b:a': self.abitrate},
                        {'-acodec': 'ac3'},
                        {'-ac': '2'}]
        args = ['ffmpeg']
        [args.extend([str(k), str(v)]) if v is not None else args.extend([str(k)]) 
         for i in enc_opts for (k,v) in i.items()]
        
        if self.two_pass:
            args.extend(['-pass', passnum, '-passlogfile', self.log_file])
            if passnum == '1':
                args.extend(['-y', '/dev/null'])
            elif passnum == '2':
                args.append(self.out_file)
        else:
            args.append(self.out_file)
        return args
    
    def encode(self):
        first_pass = self.build_cmd(1)
        print('First pass: \n{}\n'.format(' '.join(first_pass)))
        
        if not self.dry_run:
            subprocess.check_call(first_pass)
        
        if self.two_pass:
            second_pass = self.build_cmd(2)
            print('\n{}\n\nSecond pass: \n{}\n'.format('='*78 , 
                                                       ' '.join(second_pass)))
            if not self.dry_run:
                subprocess.check_call(second_pass)
        return self.out_file
                
        
def main():
    enc = Encoder(get_args=True)
    enc.encode()
    return 0

if __name__ == '__main__':
	main()

