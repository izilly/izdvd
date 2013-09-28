#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

from izdvd.dvdmenu import DVDMenu
from izdvd.encoder import Encoder
from izdvd import utils
from izdvd import user_input
from izdvd import config
import sys
import subprocess
import math
from datetime import timedelta
import os
from lxml import etree
import glob
import re
import logging


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
                 no_loop_menu=True,
                 mode='dvd'):
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
        self.mode = mode
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
        #~ self.log_menu_info()
        self.prompt_menu()
        # prepare mpeg2 files
        self.encode_video()
        self.create_dvd_xml()
        # author DVD
        if self.with_author_dvd:
            self.author_dvd()
    
    def get_out_paths(self):
        paths = utils.get_out_paths(config.PROG_NAME, self.out_name, self.out_dir,
                                    self.tmp_dir, self.dvd_size_bytes * 1.2)
        self.out_name, self.out_dir, self.tmp_dir = paths
        
        self.out_dvd_dir = os.path.join(self.out_dir, 'DVD')
        self.out_files_dir = os.path.join(self.out_dir, 'files')
        self.out_dvd_xml = os.path.join(self.out_files_dir, 
                                        '{}_dvd.xml'.format(self.out_name))
        self.out_log = os.path.join(self.out_dir, 
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
                devices[dev] = utils.get_space_available(i) - s
        if min(devices.values()) < 1024*1024:
            raise
        
        self.logger = logging.getLogger('{}.dvd'.format(config.PROG_NAME))
        self.logger.addHandler(logging.FileHandler(self.out_log))
        self.logger.setLevel(logging.INFO)
    
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
        re_tem_labeled_nums = r'({0}*(?:{1}){0}*{2}+)'.format(config.RE_PARTS_SEP, 
                                                              config.RE_VOL_PREFIXES, 
                                                              config.RE_VOL_NUMS)
        re_tem_labeled_letters = r'({0}*(?:{1}){0}*{2})'.format(config.RE_PARTS_SEP, 
                                                                config.RE_VOL_PREFIXES,
                                                                config.RE_VOL_LETTERS)
        re_tem_bare_letters = r'({0}*{1})'.format(config.RE_PARTS_SEP, 
                                                  config.RE_VOL_LETTERS)
        re_stacked_labeled_nums = re_tem.format(re_tem_labeled_nums)
        re_stacked_labeled_letters = re_tem.format(re_tem_labeled_letters)
        re_stacked_bare_letters = re_tem.format(re_tem_bare_letters)
        return [re_stacked_labeled_nums, re_stacked_labeled_letters, 
                re_stacked_bare_letters]
    
    def log_output_info(self):
        logs = list(zip(['Name', 'DVD', 'Files', 'tmp'],
                        [self.out_name, self.out_dvd_dir, self.out_files_dir, 
                         self.tmp_dir]))
        utils.log_items(logs, 'Output Paths', logger=self.logger)

    def log_input_info(self):
        utils.log_items(heading='Video Information', items=[], lines_before=1,
                        logger=self.logger)
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
            utils.log_items('#{}: {}:'.format(n+1, i['vid_label']), 
                            lines_before=0, sep_pre='-', sep_post='-', 
                            logger=self.logger)
            utils.log_items(log_data, col_width=12, indent=4, lines_before=0,
                            logger=self.logger)
    
    def log_titlesets(self):
        utils.log_items(heading='Titlesets', items=[], lines_before=1,
                        logger=self.logger)
        for n,i in enumerate(self.titlesets):
            ar = i['ar']
            seconds = sum([d['duration'] for d in i['vids']])
            duration = self.get_duration_string(seconds)
            log_data = list(zip(['Aspect Ratio', 'Duration', 'Titles'], 
                                [ar, duration, 
                                 '{} of {}'.format(len(i['vids']),
                                                   len(self.vids))]))
            log_data.append(('Videos', [v['vid_label'] for v in i['vids']]))
            utils.log_items('Titleset #{} of {}'.format(n+1, len(self.titlesets)),
                            lines_before=0, sep_pre='-', sep_post='-', 
                            logger=self.logger)
            utils.log_items(log_data, col_width=12, indent=4, lines_before=0,
                            logger=self.logger)
    
    def log_menu_info(self):
        if self.menu_ar == 16/9:
            ar = '16:9'
        else:
            ar = '4:3'
        log_data = list(zip(['Aspect Ratio', 'Image', 'Video'],
                            [ar, self.menu.bg.path_bg_img, 
                             self.menu.path_menu_mpg]))
        utils.log_items(heading='Menu', items=log_data, lines_before=1,
                        logger=self.logger)
    
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
                o = subprocess.check_call([config.VIDEO_PLAYER, path],
                                          stderr=subprocess.STDOUT,
                                          stdout=subprocess.DEVNULL)
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
                o = subprocess.check_call([config.IMAGE_VIEWER, 
                                           self.menu.bg.path_bg_img])
            elif resp == 2:
                o = subprocess.check_call([config.VIDEO_PLAYER, 
                                           self.menu.path_menu_mpg],
                                          stderr=subprocess.STDOUT,
                                          stdout=subprocess.DEVNULL)
    
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
        utils.log_items(logs, 'DVD Info', logger=self.logger)
    
    def get_audio_bitrate(self):
        return self.abitrate
    
    def log_dvd_info(self):
        pass
    
    def get_menu(self):
        utils.log_items(heading='Making DVD Menu...', items=False, 
                        sep=None, sep_post='-', logger=self.logger)
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
                            out_dir=self.out_files_dir,
                            out_name=self.out_name,
                            tmp_dir=self.tmp_dir,
                            menu_ar=self.menu_ar,
                            dvd_format=self.dvd_format,
                            out_log=self.out_log,
                            mode=self.mode,
                            **menu_args)

        self.blank_menu = DVDMenu(menu_imgs=None,
                                  out_dir=self.out_files_dir,
                                  out_name='blank_menu',
                                  tmp_dir=self.tmp_dir,
                                  menu_ar=self.menu_ar,
                                  dvd_format=self.dvd_format,
                                  frames=1,
                                  mode=self.mode,
                                  no_logging=True)
    
    def encode_video(self):
        # TODO: self.vids[n]['in'] is now a list of paths 
        if self.no_encode_v:
            utils.log_items('Skipping encoding mpeg2 video...', 
                            logger=self.logger)
            for i in self.vids:
                i['mpeg'] = i['in'][0]
            return
        utils.log_items(heading='Encoding mpeg2 video...', items=False,
                        logger=self.logger)
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
        utils.log_items(heading='Making dvdauthor xml...', items=False,
                        logger=self.logger)
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
        utils.log_items(heading='Writing DVD to disc...', items=False,
                        logger=self.logger)
        e = dict(os.environ)
        e['VIDEO_FORMAT'] = self.dvd_format
        cmd = ['dvdauthor', '-x', self.out_dvd_xml, '-o', self.out_dvd_dir]
        o = subprocess.check_output(cmd, env=e, universal_newlines=True)

