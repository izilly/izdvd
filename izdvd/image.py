#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.
#

import subprocess
import os.path
import shutil
import tempfile
import math


class Error(Exception):
    def __init__(self, message):
        self.message = message


class TextImg(Img):
    def __init__(self, text, line_height, max_width=None, font='Sans'):
        self.text = text
        self.segments = []
        self.line_height = line_height
        self.font = font
    
    def get_dims(self, segment):
        pass
    
    def get_pt_size(self):
        pass
    
    def wrap_text(self):
        pass


class Img (object):
    def __init__(self, path=None, ext='png'):
        self.uid = str(id(self))
        self.ext = ext
        self.versions = []
        self.update_versions(path)
        self.orig_name = self.name
        self.orig_ext = self.ext
        if path is not None:
            self.tmpdir = os.path.join(tempfile.gettempdir(), __name__, 
                                       self.orig_name+self.uid)
            self.width = self.get_width()
            self.height = self.get_height()
            self.orig_width = self.width
            self.orig_height = self.height
            self.ar = self.width / self.height
            self.orig_ar = self.ar
        else:
            self.tmpdir = os.path.join(tempfile.gettempdir(), __name__, 
                                       self.uid)
            self.width = None
            self.height = None
            self.orig_width = None
            self.orig_height = None
            self.ar = None
            self.orig_ar = None
        if not os.path.exists(self.tmpdir):
            os.makedirs(self.tmpdir)
        self.x_offset = 0
        self.y_offset = 0
    
    def update_versions(self, new_version):
        self.path = new_version
        self.versions.append(new_version)
        if new_version is not None:
            self.basename = os.path.basename(self.path)
            self.name, self.ext = os.path.splitext(self.basename)
        else:
            self.basename = None
            self.name = self.uid
    
    def get_tmpfile(self, suffix, out_fmt):
        filename = '{}_{}.{}'.format(self.name, suffix, out_fmt)
        out_file = os.path.join(self.tmpdir, filename)
        return out_file

    def get_width(self):
        w = subprocess.check_output(['identify', '-format', '%w', self.path], 
                                    universal_newlines=True)
        w = int(w.strip())
        return w

    def get_height(self):
        h = subprocess.check_output(['identify', '-format', '%h', self.path], 
                                    universal_newlines=True)
        h = int(h.strip())
        return h
    
    def update_dims(self):
        self.width = self.get_width()
        self.height = self.get_height()
        return (self.width, self.height)
        
    def clear_offsets(self):
        '''Resets any saved offset information.  Any future operations which 
        record offset information will be relative to this location, rather
        than the original image.
        '''
        self.x_offset = 0
        self.y_offset = 0
    
    def write(self, overwrite=False, out_dir=None, 
              out_basename=None, suffix_name=True, backup=True):
        if overwrite:
            if backup:
                bak = shutil.move(self.versions[0], self.versions[0]+'.bak')
            written = shutil.copy(self.path, self.version[0])
            self.update_versions(written)
            return written
        if out_dir is None:
            out_dir = self.tmpdir
        if out_basename is None:
            if suffix_name is True:
                out_basename = self.basename
            else:
                out_basename = self.orig_name+self.ext
        out_path = os.path.join(out_dir, out_basename)
        if os.path.exists(out_path):
            if os.path.samefile(out_path, self.path):
                return out_path
            else:
                bak = shutil.move(out_path, out_path+'.bak')
        written = shutil.copy(self.path, out_path)
        self.update_versions(written)
        return written
    
    def transcode(self, out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('tc', out_fmt)
        o = subprocess.check_output(['convert', self.path, out_file], 
                                    universal_newlines=True)
        self.update_versions(out_file)
        return out_file
    
    def resize(self, width, height, ignore_aspect=False, out_file=None, 
               out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('{}x{}'.format(width, height), out_fmt)
        flags=''
        if ignore_aspect:
            flags='!'
        size = '{}x{}{}'.format(width, height, flags)
        o = subprocess.check_output(['convert', self.path, '-resize', size, 
                                     out_file], universal_newlines=True)
        self.update_versions(out_file)
        return out_file
    
    def pad(self, color='none', north=0, south=0, east=0, west=0, 
            out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('padded', out_fmt)
        splice_opts = []
        for k,v in {'north':north, 'south':south}.items():
            if v > 0:
                splice_opts.extend(['-gravity', k, '-splice', '0x{}'.format(v)])
        for k,v in {'east':east, 'west':west}.items():
            if v > 0:
                splice_opts.extend(['-gravity', k, '-splice', '{}x0'.format(v)])
        print(splice_opts)
        cmd = ['convert', self.path, '-background', color]
        cmd.extend(splice_opts)
        cmd.append(out_file)
        o = subprocess.check_output(cmd, universal_newlines=True)
        self.update_versions(out_file)

    def pad_centered(self, color='none', pad_x=0, pad_y=0, out_file=None, 
                     out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('padded', out_fmt)
        new_w = self.get_width() + pad_x
        new_h = self.get_height() + pad_y
        self.pad_to(color=color, new_w=new_w, new_h=new_h, out_file=out_file,
                    out_fmt=out_fmt)

    def pad_to(self, color='none', new_w=None, new_h=None, out_file=None, 
                     out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('padded', out_fmt)
        extent_dims = '{}x{}'.format(new_w, new_h)
        o = subprocess.check_output(['convert', self.path, '-gravity', 'center',
                                     '-background', color, '-extent', 
                                     extent_dims, out_file], 
                                    universal_newlines=True)
        self.update_versions(out_file)
    
    def pad_to_ar(self, ar, color='none', out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('pad_ar', out_fmt)
        if ar > self.ar:
            new_w = math.ceil(self.height * ar)
            new_h = self.height
        elif ar < self.ar:
            new_w = self.width
            new_h = math.ceil(self.width / ar)
        else:
            return
        self.pad_to(color, new_w, new_h, out_file, out_fmt)
    
    def border(self, color, geometry, out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('border', out_fmt)
        before_w, before_h = self.update_dims()
        o = subprocess.check_output(['convert', self.path, '-compose', 'Copy', 
                                     '-bordercolor', color, '-border', 
                                     str(geometry), out_file], 
                                    universal_newlines=True)
        self.update_versions(out_file)
        new_w, new_h = self.update_dims()
        new_x_offset = (new_w-before_w)/2
        new_y_offset = (new_h-before_h)/2
        self.x_offset += new_x_offset
        self.y_offset += new_y_offset
        return out_file
    
    def drop_shadow(self, color='black', opacity=80, sigma=3, 
                    x_offset=5, y_offset=5, out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('shadow', out_fmt)
        shadow_opts = '{}x{}{:+}{:+}'.format(opacity, sigma, x_offset, y_offset)
        o = subprocess.check_output(['convert', self.path, '(', '+clone', 
                                     '-background', color, '-shadow', 
                                     shadow_opts, ')', '+swap', '-background', 
                                     'none', '-layers', 'merge', '+repage', 
                                     out_file], 
                                    universal_newlines=True)
        # calculate new offset (cannot be less than 0)
        canvas_padding = sigma*2
        new_x_offset = canvas_padding - x_offset
        if new_x_offset < 0:
            new_x_offset = 0
        new_y_offset = canvas_padding - y_offset
        if new_y_offset < 0:
            new_y_offset = 0
        # add new offset to existing offset
        self.x_offset += new_x_offset
        self.y_offset += new_y_offset
        self.update_versions(out_file)
        return out_file
    
    def overlay_onto(self, img, x_offset, y_offset, layers_method):
        '''Overlay self onto img. Does not modify self or create a new version.
        Returns:  new composed image.
        '''
        pass
    
    def new_layer(self, img, x_offset, y_offset, use_orig_origin=False, 
                  layers_method='merge', out_file=None, out_fmt='png'):
        '''Overlay img onto self.  Modifies self and adds a new version with
        img composed onto self (and flattened).  Does not modify img.
        Returns:  self (with new layer flattened onto canvas)
        '''
        if out_file is None:
            out_file = self.get_tmpfile('new_layer', out_fmt)
        if type(img) == type(self):
            if use_orig_origin:
                x_offset -= img.x_offset
                y_offset -= img.y_offset
            img = img.path
        offsets = '{:+}{:+}'.format(x_offset, y_offset)
        o = subprocess.check_output(['convert', self.path, '-background', 'none', 
                                     '-page', offsets, img, 
                                     '-layers', layers_method, '+repage', 
                                     out_file], 
                                    universal_newlines=True)
        if x_offset < 0:
            self.x_offset += abs(x_offset)
        if y_offset < 0:
            self.y_offset += abs(y_offset)
        self.update_versions(out_file)
        return out_file
    
    def new_canvas(self, color='none', out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('canvas', out_fmt)
        o = subprocess.check_output(['convert', self.path, '-background', 
                                     color, '-compose', 'Dst', '-flatten', 
                                     out_file], 
                                    universal_newlines=True)
        return Img(out_file)

