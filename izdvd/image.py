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
from collections import deque
import re


class Error(Exception):
    def __init__(self, message):
        self.message = message


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
            self.basename = '{}.{}'.format(self.uid, self.ext)
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
    
    def show(self):
        cmd = ['display', self.path]
        subprocess.check_call(cmd)
    
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
    
    def append(self, img_list, vertical=True, gravity='center', 
               background='none', padding=0, out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('new_layer', out_fmt)
        imgs = [i.path if isinstance(i, type(self)) else i for i in img_list]
        if padding:
            if vertical:
                pad_size = '0x{}'.format(padding)
            else:
                pad_size = '{}x0'.format(padding)
            pad_img = ['-size', pad_size, 
                       'xc:{}'.format(background)]
            img_list = []
            for i in imgs:
                img_list.extend(pad_img)
                img_list.append(i)
            imgs = img_list
        if vertical:
            append_op = '-'
        else:
            append_op = '+'
        o = subprocess.check_output(['convert', self.path, 
                                     '-background', background,
                                     '-gravity', gravity] 
                                     + imgs 
                                     + ['{}append'.format(append_op), out_file], 
                                    universal_newlines=True)
        self.update_versions(out_file)
        return out_file


class TextImg(Img):
    def __init__(self, text, font='DejaVu-Sans-Bold', pointsize=None,
                 fill='white', stroke='black', strokewidth=0, word_spacing=0,
                 clear_inner_stroke=True,
                 line_height=None, max_width=None, max_lines=None, 
                 size=None, background='none', gravity='center'):
        self.text = text
        self.font = font
        self.pts = pointsize
        self.fill = fill
        self.stroke = stroke
        self.strokewidth = strokewidth
        self.interword_spacing = word_spacing
        self.clear_inner_stroke = clear_inner_stroke
        self.line_height = line_height
        self.max_width = max_width
        self.max_lines = max_lines
        self.size = size
        self.background = background
        self.gravity = gravity
        self.ref_text = '{}{}{}'.format('1234567890', 
                                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
                                        'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.lower())
        self.lines = []
        self.line_imgs = []
        #
        if self.pts is None and self.line_height is not None:
            self.pts = self.get_pts_from_lh()
            self.pts_orig = self.pts
        if self.max_width:
            self.wrap_text()
        else:
            self.lines = [self.text.split(' ')]
        self.get_draw_cmd = self.get_annotate_cmd
        super(TextImg, self).__init__()
        self.write()
        if self.max_width:
            self.append_lines()
    
    def get_common_opts(self, interword_spacing=None, undercolor=None):
        opts = []
        opt_names = ['background', 'gravity', 'font', 'fill', 'stroke', 
                     'strokewidth']
        for i in opt_names:
            v = getattr(self, i)
            if v is not None:
                opts.append('-{}'.format(i.replace('_', '-')))
                opts.append(str(v))
        if interword_spacing is None:
            interword_spacing = self.interword_spacing
        opts.extend(['-interword-spacing', str(interword_spacing)])
        if undercolor is not None:
            opts.extend(['-undercolor', undercolor])
        return opts
    
    def get_label_cmd(self, pts=None, text=None, size=None, undercolor=None,
                      interword_spacing=None):
        if text is None:
            text = self.text
        if pts is None:
            pts = self.pts
        common_opts = self.get_common_opts(interword_spacing=interword_spacing,
                                           undercolor=undercolor)
        if size:
            size = '{}x{}'.format(*size)
            common_opts = ['-size', size] + common_opts
        draw_opts = ['-pointsize', str(pts), 'label:{}'.format(text)]
        cmd = ['convert'] + common_opts + draw_opts
        return cmd
    
    def get_annotate_cmd(self, size=None, text=None, pts=None, 
                          clear_inner_stroke=None, interword_spacing=None):
        if size is None:
            size = self.get_size(text=text, pts=pts, 
                                 interword_spacing=interword_spacing)
        cmd = self.get_annotate_opts(size=size, text=text, pts=pts, 
                                      clear_inner_stroke=clear_inner_stroke,
                                      interword_spacing=interword_spacing)
        return cmd
        
    def get_annotate_opts(self, size=None, text=None, pts=None, 
                          clear_inner_stroke=None, interword_spacing=None,
                          use_undercolor=False):
        if text is None:
            text = self.text
        if pts is None:
            pts = self.pts
        if size is None:
            h = len(text.splitlines()) * pts * 10 + self.strokewidth * 10
            w = len(text) * pts * 10 + self.strokewidth * 10
        else:
            w, h = size
        if clear_inner_stroke is None:
            clear_inner_stroke = self.clear_inner_stroke
        if interword_spacing is None:
            interword_spacing = self.interword_spacing
        
        size = '{}x{}'.format(w, h)
        undercolor = 'magenta'
        if self.background == 'magenta':
            undercolor = 'cyan'

        canvas_opts = ['-size', size, 'xc:{}'.format(self.background)]
        common_opts = self.get_common_opts(interword_spacing=interword_spacing)
        draw_opts = ['-pointsize', str(pts), '-annotate', '0', text]
        if use_undercolor:
            draw_opts = ['-undercolor', undercolor] + draw_opts
        if clear_inner_stroke:
            draw_opts += ['-stroke', 'none', '-annotate', '0', text]
        format_opts = ['-format', '%w;%h;%X;%Y']
        
        cmd = ['convert'] + canvas_opts + common_opts + draw_opts + format_opts
        return cmd
    
    def get_size(self, text=None, pts=None, interword_spacing=None):
        cmd_h = self.get_annotate_opts(text=self.ref_text, pts=pts, 
                                      interword_spacing=interword_spacing,
                                      use_undercolor=True,
                                      clear_inner_stroke=False)
        cmd_h += ['-trim', 'info:']
        cmd_w = self.get_annotate_opts(text=text, pts=pts, 
                                      interword_spacing=interword_spacing,
                                      use_undercolor=True,
                                      clear_inner_stroke=False)
        cmd_w += ['-trim', 'info:']
        out_h = subprocess.check_output(cmd_h, universal_newlines=True)
        out_w = subprocess.check_output(cmd_w, universal_newlines=True)
        z,h,z,z = out_h.split(';')
        w,z,z,z = out_w.split(';')
        return (float(w), float(h))
    
    def write(self, cmd=None, out_dir=None, out_basename=None):
        if cmd is None:
            cmd = self.get_draw_cmd()
        if out_dir is None:
            out_dir = self.tmpdir
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        if out_basename is None:
            out_basename = self.basename
        out_path = os.path.join(out_dir, out_basename)
        cmd = cmd + [out_path]
        output = subprocess.check_output(cmd, universal_newlines=True)
        written = out_path
        self.update_versions(written)
        return written
    
    def get_line_imgs(self):
        line_imgs = []
        for line in self.lines:
            text = ' '.join(line)
            img = TextImg(text=text, font=self.font, pointsize=self.pts,
                          fill=self.fill, stroke=self.stroke, 
                          strokewidth=self.strokewidth, 
                          word_spacing=self.interword_spacing,
                          clear_inner_stroke=self.clear_inner_stroke,
                          line_height=None, 
                          max_width=None, max_lines=None, 
                          size=self.size, background=self.background, 
                          gravity=self.gravity)
            line_imgs.append(img)
        self.line_imgs = line_imgs
    
    def append_lines(self, out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('wrapped', out_fmt)
        if not self.line_imgs:
            self.get_line_imgs()
        li = [i.path for i in self.line_imgs]
        top = li[0]
        bottom = li[1:]
        append_cmd = ['convert', top, '-background', self.background, 
                      '-gravity', self.gravity] + bottom + ['-append', out_file]
        o = subprocess.check_output(append_cmd, universal_newlines=True)
        self.update_versions(out_file)
        return out_file
    
    def show(self, cmd=None):
        if cmd is None:
            cmd = ['display', self.path]
        else:
            cmd = cmd + ['show:']
        subprocess.check_call(cmd)
    
    def get_pts_from_lh(self):
        results = []
        pts = 0
        while True:
            pts += 1
            w,h = self.get_size(pts=pts)
            results.append((pts, h))
            if h > self.line_height:
                pt_size = pts - 1
                return pt_size
    
    def get_default_word_spacing(self, pts=None):
        zero, h = self.get_size(pts=pts, text='A A', interword_spacing=0)
        one, h = self.get_size(pts=pts, text='A A', interword_spacing=1)
        default = zero - one + 1
        return default
    
    def wrap_text(self):
        self._fit_wrapping()
        self._maximize_pts()
        self._minimize_raggedness()
        self._maximize_word_spacing()
        self._ellipsize_lines()
        #~ self.lines = self._split_lines(self.text)
    
    def _fit_wrapping(self, pts_adjust=.1, spacing_adjust=.5):
        pts = self.pts
        pts_min = pts - pts * pts_adjust
        spacing = self.get_default_word_spacing()
        spacing_min = spacing - spacing * spacing_adjust
        
        lines_default = self._split_lines(self.text, pts, 0)
        lines_default['len_excluded'] = self._count_words(lines_default)

        lines_min = self._split_lines(self.text, pts_min, spacing_min)
        lines_min['len_excluded'] = self._count_words(lines_min)
        
        if lines_min['len_excluded'] == lines_default['len_excluded']:
            self.lines = lines_default
            return
        
        lines_med = self._split_lines(self.text, pts, spacing_min)
        lines_med['len_excluded'] = self._count_words(lines_med)
        
        self.interword_spacing = spacing_min
        
        if lines_med['len_excluded'] == lines_min['len_excluded']:
            self.lines = lines_med
            return
        else:
            self.pts = pts_min
            self.lines = lines_min
            return
    
    def _split_lines(self, text, pts=None, interword_spacing=None):
        words = text.split(' ')
        lines = [{'line':[], 'trim':False}]
        while words:
            w = words.pop(0)
            width, h = self.get_size(' '.join(lines[-1]['line'] + [w]), pts,
                                     interword_spacing)
            if width <= self.max_width:
                lines[-1]['line'].append(w)
            elif not lines[-1]['line']:
                lines[-1]['line'].append(w)
                lines[-1]['trim'] = self._get_trimmed_len(lines[-1]['line'], pts, 
                                                         interword_spacing)
            else:
                if len(lines) == self.max_lines:
                    words = [w] + words
                    break
                else:
                    lines.append({'line':[w], 'trim':False})
        if words:
            for i in range(len(words)+1):
                trim = self._get_trimmed_len(lines[-1]['line']+words[:i], pts,
                                             interword_spacing)
                if trim:
                    lines[-1]['trim'] = trim
                    lines[-1]['line'].extend(words[:i])
                    words = words[i:]
                    break
        return {'used': lines, 'unused': words}
    
    def _get_trimmed_len(self, line, pts=None, interword_spacing=None):
        text = ' '.join(line)
        for i in range(len(text)+1):
            width,h = self.get_size(text[:i]+'...', pts=pts, 
                                    interword_spacing=interword_spacing)
            if width > self.max_width:
                return i - 1
        return False
    
    def _ellipsize_lines(self, pts=None, interword_spacing=None):
        for i in self.lines['used']:
            i['trim'] = self._get_trimmed_len(i['line'], pts, interword_spacing)

    def _count_words(self, lines):
        trimmed = len([i for i in lines['used'] if i['trim']])
        unused = len(lines['unused']) + trimmed
        return unused
    
    def _get_unused_w_sq(self, lines, pts=None, interword_spacing=None):
        unused_w_sq = 0
        for i in lines:
            w,h = self.get_size(' '.join(i), pts, interword_spacing)
            u = (self.max_width - w) ** 2
            unused_w_sq += u
        return unused_w_sq
    
    def _minimize_raggedness(self, pts=None, interword_spacing=None):
        max_w = self.max_width
        lines = self.lines['used']
        for i in reversed(range(1, len(lines))):
            if lines[i]['trim']:
                continue
            line = lines[i]['line']
            prev = lines[i-1]['line']
            for word in reversed(prev):
                new_line = prev[-1:] + line
                new_prev = prev[:-1]
                w,h = self.get_size(' '.join(new_line), pts, interword_spacing)
                if w <= max_w:
                    cur_space_sq = self._get_unused_w_sq([line, prev], pts,
                                                         interword_spacing)
                    new_space_sq = self._get_unused_w_sq([new_line, new_prev],
                                                         pts, interword_spacing)
                    if new_space_sq < cur_space_sq:
                        line[:0] = [prev.pop()]
                    else:
                        break
                else:
                    break
        self.lines['used'] = lines

    def _maximize_pts(self):
        pts = math.floor(self.pts) - 1
        while True:
            pts += 1
            if pts > self.pts_orig:
                self.pts = self.pts_orig
                return
            lines = self._split_lines(self.text, pts)
            excluded = self._count_words(lines)
            if excluded > self.lines['len_excluded']:
                break
        self.pts = pts - 1

    def _maximize_word_spacing(self):
        dws = self.get_default_word_spacing()
        iws = self.interword_spacing
        i = dws * .05
        while True:
            iws += i
            if iws >= dws:
                self.interword_spacing = 0
                return
            lines = self._split_lines(self.text, interword_spacing=iws)
            excluded = self._count_words(lines)
            if excluded > self.lines['len_excluded']:
                break
        self.interword_spacing = iws - i


class CanvasImg(Img):
    def __init__(self, width, height, color='none'):
        self.size = width, height
        self.color=color
        super(CanvasImg, self).__init__()
        self.write()
    
    def write(self, out_file=None, out_fmt='png'):
        if out_file is None:
            out_file = self.get_tmpfile('canvas', out_fmt)
        o = subprocess.check_output(['convert', 
                                     '-size', '{}x{}'.format(*self.size),
                                     'xc:{}'.format(self.color),
                                     out_file], universal_newlines=True)
        self.update_versions(out_file)
        return out_file
        
        


class _PangoTextImg(Img):
    def __init__(self, text, line_height, font='Sans'):
        self.text = text
        self.line_height = line_height
        self.font = font
    
    def get_pt_size(text, font, lh):
        pts = 0
        while True:
            pts += 1
            pango = 'pango:<span font="{} {}">{}</span>'.format(font, pts, 
                                                                text)
            height = subprocess.check_output(['convert', pango, '-format', '%h',
                                              'info:-'], universal_newlines=True)
            if int(height) > lh:
                pt_size = pts - 1
                return pt_size


