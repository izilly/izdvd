#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.

from izdvd.menu import DVD, DVDMenu, BG
from izdvd.utils import HelpFormatter
import re
import os
import os.path
import argparse
import sys


def get_options(mode='dvd'):
    desc = {}
    desc['dvd'] = '''Make an authored DVD with menu.  Outputs a VIDEO_TS 
                     directory with DVD video files as well as a "files" 
                     directory containing the files used to make the DVD 
                     (dvdauthor/spumux xml configuration files, menu 
                     image/video files, etc).'''
    desc['menu'] = '''Make a DVD Menu. Outputs a set of video and xml files 
                      compatible with dvdauthor.'''
    desc['bg'] = '''Make a DVD menu background.  Outputs a set of 
                    image and xml files that can be used to create a DVD menu 
                    with spumux (part of the dvdauthor package).''' 
    
    parser = argparse.ArgumentParser(formatter_class=HelpFormatter, 
                                     description=desc[mode])
    add_in_paths_opts(parser, mode)

    if mode == 'dvd':
        add_in_opts(parser, mode)
        add_dvd_opts(parser, mode)
        
    add_menu_opts(parser, mode)
    add_out_paths_opts(parser, mode)
    
    options = parser.parse_args()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit()

    return options

    
def add_in_paths_opts(parser, mode='dvd'):
    desc = {}
    desc['dvd'] = '''Input video files can be given either with --in-dirs 
                     (directories containing video[/image/subtitle] files) or 
                     with --in-vids (the video files themselves).  With either 
                     option, menu-images and subtitle files will be 
                     automatically added if they can be found in the same 
                     directory as the video (same/similar name to the video, 
                     folder.jpg, poster.png, etc), however, the --in-srts 
                     and/or --menu-imgs options can be used to override this 
                     behavior.  Menu labels will be inferred from the video 
                     filenames (unless --label-from-dir or --label-from-img is 
                     used) but are not added to the menu by default unless 
                     --with-menu-labels is given or the --menu-labels option is 
                     used to specify the text to be used for the 
                     labels.'''  


    in_files = parser.add_argument_group(title='Input Paths')

    if mode in ['dvd']:
        in_files.description = desc['dvd']

    if mode == 'dvd':
        in_files.add_argument('-v', '--in-vids', metavar='PATH', nargs='*',
                                  help="""Video files""")
        in_files.add_argument('-d', '--in-dirs', metavar='PATH', nargs='*', 
                                  help="""Directories containing 
                                          video[/image/subtitle] files""")
        in_files.add_argument('-s', '--in-srts', metavar='PATH', nargs='*', 
                                  help="""Subtitle files in .srt format""")
    
    if mode in ['dvd', 'menu', 'bg']:
        in_files.add_argument('-i', '--menu-imgs', metavar='PATH', nargs='*', 
                                  help="""Menu images (buttons)""")
        in_files.add_argument('-l', '--menu-labels', metavar='LABEL', nargs='*', 
                                  help="""Menu labels (optional)""")
        in_files.add_argument('-b', '--menu-bg', metavar='PATH', default='gray',
                                  help="""Menu background image (optional). 
                                          May be given as a path to an image 
                                          file or as a color name/value, e.g., 
                                          "white" or "#ffffff".  (default: 
                                          %(default)s)""")
    if mode in ['dvd', 'menu']:
        in_files.add_argument('-a', '--menu-audio', metavar='PATH', 
                                 help="""Audio file to be used as audio for
                                         the menu (optional).  If this option 
                                         is not given, a silent audio track 
                                         will be used instead.""")

def add_in_opts(parser, mode='dvd'):
    in_opts = parser.add_argument_group(title='Input Options')

    in_opts.add_argument('--vid-fmts', metavar='FMT', nargs='*', 
                             default=['mp4', 'avi', 'mkv'], 
                             help="""If in-vids are not specified, search 
                                     in-dirs for video files with these 
                                     extensions""")
    in_opts.add_argument('--img-fmts', metavar='FMT', nargs='*', 
                             default=['png', 'jpg', 'bmp', 'gif'], 
                             help="""If menu-imgs are not specified, search 
                                     video directories for image files with 
                                     these extensions""")
    in_opts.add_argument('--img-names', metavar='NAME', nargs='*', 
                             default=['poster', 'folder'],
                             help="""If menu-imgs are not specified, search 
                                     video directories for image files with 
                                     these names (in addition to the video 
                                     names themselves)""")
    in_opts.add_argument('--multiple-vids-per-dir', action='store_false',
                             dest='one_vid_per_dir', default=True,
                             help="""Normally, if in-vids are not specified, 
                                     in-dirs are assumed to contain one 
                                     video each. With this option all of the 
                                     video files in each in-dir are added. 
                                     Incompatible with the img-names option; 
                                     images are only searched for using the 
                                     name of the video""")
    in_opts.add_argument('--with-menu-labels', action='store_true', 
                             default=False, 
                             help="""This option adds labels below the 
                                     menu-imgs even if the --menu-labels option 
                                     is not given. The labels are inferred from 
                                     the video filenames unless the 
                                     --label-from-dir or --label-from-img 
                                     options are given.""")    
    in_opts.add_argument('--label-from-img', action='store_true',
                             help="""Infer menu-labels from menu-img 
                                     filenames instead of the default of 
                                     using the video filename""")
    in_opts.add_argument('--label-from-dir', action='store_true',
                             help="""Infer menu-labels from directory names 
                                     instead of the default of using the video 
                                     filename""")
    in_opts.add_argument('--strip-label-year', action='store_true',
                             help="""Strip parenthesized year from end of 
                                     inferred labels. e.g., "label (2013)" -> 
                                     "label".""")
    in_opts.add_argument('--no-encode-v', action='store_true',
                             help="""Skip encoding of video files.  Assume 
                                     video files are DVD compliant mpeg2.""")
    in_opts.add_argument('--unstack-vids', action='store_true',
                             help='''Treat multiple input video files as a
                                     single video when their names only 
                                     differ by certain rules. e.g., 
                                     "video.cd1.ext", "video.cd2.ext"''')

def add_dvd_opts(parser, mode='dvd'):
    dvd_opts = parser.add_argument_group(title='DVD Options')
    dvd_opts.add_argument('--audio-lang', metavar='LANG', default='en', 
                              help="""Audio Language. 
                                      (default: %(default)s)""")
    dvd_opts.add_argument('--with-subs', action='store_true', default=False,
                              help="""Search for matching subtitle files in the 
                                      directory of each video""")
    dvd_opts.add_argument('--sub-lang', metavar='LANG', default='en', 
                              help="""Subtitle language. (default: 
                                      %(default)s)""")
    dvd_opts.add_argument('--dvd-ar', choices=['16:9', '4:3'], default=None,
                              help="""DVD aspect ratio.  If not specified, it 
                                      will be calculated automatically.""")
    dvd_opts.add_argument('--vbitrate', metavar='BPS', type=int, 
                              help="""Video bitrate in bits per second. If not 
                                      specified it will be calculated 
                                      automatically based on dvd-size.""")
    dvd_opts.add_argument('--abitrate', metavar='BPS', type=int, 
                              default=196608,
                              help="""Audio bitrate in bits per second. 
                                      (default: %(default)s (192kbps))""")
    dvd_opts.add_argument('--no-two-pass', action='store_false', default=True,
                              dest='two_pass',
                              help="""Don't use two-pass encoding.""")
    dvd_opts.add_argument('--no-separate-titlesets', action='store_false', 
                              default=True, dest='separate_titlesets',
                              help="""By default, the DVD will be made with 
                                      separate titlesets if there are both 
                                      4:3 and 16:9 videos present. This 
                                      option overrides that behavior and 
                                      puts everything in a single titleset, 
                                      cropping/padding the video so that 
                                      everything uses the same aspect 
                                      ratio.""")
    dvd_opts.add_argument('--no-separate-titles', action='store_false', 
                              default=True, dest='separate_titles',
                              help="""By default every video will be placed 
                                      in its own title on the DVD. This 
                                      option overrides that behavior and 
                                      puts everything in a single title.  
                                      Each video will be a chapter in the 
                                      title.""")
    dvd_opts.add_argument('--no-loop-menu', action='store_true', 
                              default=False, 
                              help="""Normally the menu plays in a loop 
                                      until a title is selected.  With this
                                      option the menu plays once and then 
                                      starts playing the first title.""")
    dvd_opts.add_argument('--no-menu', action='store_false', dest='with_menu', 
                              default=True,
                              help="""Don't make a menu for the DVD""")
    dvd_opts.add_argument('--no-author-dvd', action='store_false', 
                              dest='with_author_dvd', default=True,
                              help="""Output an xml file that can be used 
                                      with dvdauthor, but don't actually 
                                      create the DVD files""")
    dvd_opts.add_argument('--dvd-size', type=int, default=4700372992, 
                              dest='dvd_size_bytes', metavar='BYTES', 
                              help="""Size of DVD media in bytes. The default 
                                      of 4700372992 is the size of a 
                                      single-layer DVD +R, which is slightly 
                                      smaller than a DVD-R, so will work for 
                                      either one. DVD-R=4707319808, DVD 
                                      +R=4700372992, DVD-R DL=8543666176, 
                                      DVD+R DL= 8547991552.  (default: 
                                      %(default)s)""")

def add_menu_opts(parser, mode='dvd'):
    bg_opts = parser.add_argument_group(title='Menu Options')

    # --menu-ar
    menu_ar = bg_opts.add_argument('--menu-ar', choices=['16:9', '4:3'])
    if mode in ['dvd']:
        menu_ar.help = """Menu aspect ratio. Without this option, it defaults
                          to 16:9 unless all titles are 4:3, or, if the 
                          --dvd-ar option is given it defaults to match 
                          --dvd-ar."""
    elif mode in ['menu', 'bg']:
        menu_ar.default = '16:9'
        menu_ar.help = """Menu aspect ratio. (default: %(default)s)"""
    
    bg_opts.add_argument('--dvd-format', metavar='FMT', 
                               default='NTSC',
                               help="""DVD format. 
                                       (NTSC or PAL, default: %(default)s)""")
    bg_opts.add_argument('--outer-padding', type=int, metavar='PX', 
                               default=80,
                               help="""Minimum padding in pixels between the 
                                       edge of the menu background and the 
                                       menu-imgs. (default: %(default)s)""")
    bg_opts.add_argument('--inner-padding', type=int, metavar='PX', 
                               default=40,
                               help="""Minimum padding in pixels between 
                                       each menu button. (default: 
                                       %(default)s)""")
    bg_opts.add_argument('--label-padding', type=int, metavar='PX', 
                               default=5,
                               help="""Minimum padding in pixels between the 
                                       menu buttons and labels. 
                                       (default: %(default)s)""")

    bg_opts.add_argument('--label-line-height', type=int, metavar='PX', 
                               default=18,
                               help="""Line height in pixels for the 
                                       menu-labels. (default: %(default)s)""")
    bg_opts.add_argument('--label-lines', type=int, metavar='N', 
                               default=2,
                               help="""Max number of lines for the 
                                       menu-labels. Text will be ellipsized 
                                       if it would require more than this 
                                       many lines. (default: %(default)s)""")


    bg_opts.add_argument('--button-border-color', metavar='COLOR', 
                             default='white',
                             help="""Color of the border drawn around each
                                     button (menu-img).""")
    bg_opts.add_argument('--button-border-thickness', metavar='PX', type=int,
                             default=5,
                             help="""Size in pixels of the border drawn 
                                     around each button (menu-img). """)
    bg_opts.add_argument('--button-highlight-color', metavar='COLOR', 
                             default='#56B356',
                             help="""Color of the highlight/border drawn 
                                     around the currently selected button 
                                     (menu-img) while the menu is navigated 
                                     using a remote/keyboard.""")
    bg_opts.add_argument('--button-highlight-thickness', metavar='PX', type=int,
                             default=10,
                             help="""Size in pixels of the highlight/border 
                                     drawn around the currently selected 
                                     button (menu-img) while the menu is 
                                     navigated using a remote/keyboard. Note 
                                     that the highlight is drawn on top of 
                                     the button-border, not outside of it.  
                                     Therefore, to make it thicker than the 
                                     button-border, this value must be 
                                     larger than --button-border-thickness. 
                                     This is recommended, especially for a 
                                     menu with only two buttons, otherwise 
                                     it is difficult to determine which 
                                     button is currently highlighted.""")
    bg_opts.add_argument('--button-select-color', metavar='COLOR', 
                             default='red',
                             help="""Color of the border drawn around the
                                     button (menu-img) for a moment 
                                     immediately after it has been "clicked" 
                                     with the remote/keyboard. The thickness 
                                     is the same as the value given with 
                                     --button-highlight-thickness.""")


def add_out_paths_opts(parser, mode='dvd'):
    out_files = parser.add_argument_group(title='Output Paths')
    out_files.add_argument('-o', '--out-dir', metavar='PATH',
                               help="""Output directory""")
    out_files.add_argument('-t', '--tmp-dir', metavar='PATH',
                               help="""Temp directory (for transcoding video 
                                       files, etc.) By default /tmp, or 
                                       whatever tempfile.gettempdir() returns 
                                       will be used if there is enough space 
                                       available.""")
    out_files.add_argument('-n', '--out-name', metavar='NAME',
                               help="""Base name prefix for generated files 
                                       (menu, log, etc)""")

# ----------------------------------------------------------------------------

def make_dvd(options):

    dvd = DVD(
              # input 
              in_vids=options.in_vids,
              in_dirs=options.in_dirs, 
              in_srts=options.in_srts, 
              menu_imgs=options.menu_imgs, 
              menu_labels=options.menu_labels, 
              menu_bg=options.menu_bg, 
              # input options
              vid_fmts=options.vid_fmts,
              img_fmts=options.img_fmts,
              #~ sub_fmts=options.sub_fmts,
              img_names=options.img_names,
              one_vid_per_dir=options.one_vid_per_dir,
              label_from_img=options.label_from_img,
              label_from_dir=options.label_from_dir, 
              strip_label_year=options.strip_label_year,
              no_encode_v=options.no_encode_v, 
              #~ no_encode_a=options.no_encode_a, 
              unstack_vids=options.unstack_vids,
              # output locations
              out_name=options.out_name, 
              out_dir=options.out_dir, 
              tmp_dir=options.tmp_dir,
              # output options
              with_menu=options.with_menu, 
              #~ menu_only=options.menu_only,
              with_author_dvd=options.with_author_dvd,
              #~ dvd_size_bits=options.#~ dvd_size_bits,
              dvd_size_bytes=options.dvd_size_bytes,
              # dvd options
              audio_lang=options.audio_lang,
              # TODO: change with_subs default to None and let DVD() add them
              # if any present or given on command line
              with_subs=options.with_subs, 
              sub_lang=options.sub_lang, 
              dvd_format=options.dvd_format, 
              dvd_ar=options.dvd_ar, 
              vbitrate=options.vbitrate, 
              abitrate=options.abitrate, 
              two_pass=options.two_pass,
              separate_titles=options.separate_titles, 
              separate_titlesets=options.separate_titlesets, 
              #~ ar_threshold=options.ar_threshold,
              # menu options
              menu_ar=options.menu_ar,
              with_menu_labels=options.with_menu_labels, 
              label_line_height=options.label_line_height,
              label_lines = options.label_lines,
              label_padding = options.label_padding,
              outer_padding = options.outer_padding,
              inner_padding = options.inner_padding,
              no_loop_menu=True)

def make_menu(options):
    menu = DVDMenu(**vars(options))

def make_bg(options):
    bg = BG(**vars(options))

def main(mode='dvd'):
    options = get_options(mode=mode)
    if mode == 'dvd':
        make_dvd(options)
    elif mode == 'menu':
        make_menu(options)
    elif mode == 'bg':
        make_bg(options)
    return 0

if __name__ == '__main__':
    main()
