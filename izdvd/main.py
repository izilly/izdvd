#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.

from izdvd.menu import DVD
from izdvd.utils import HelpFormatter
import re
import os
import os.path
import argparse


def get_options():
    mv_path = 'PATH'
    parser = argparse.ArgumentParser(formatter_class=HelpFormatter)
    in_files = parser.add_argument_group(title='Input files')

    in_files.add_argument('-v', '--in-vids', metavar=mv_path, nargs='*',
                         help='Source video files')

    in_files.add_argument('-d', '--in-dirs', metavar=mv_path, nargs='*', 
                         help='Directories, each containing a single video[/image/subtitle]')

    in_files.add_argument('-s', '--in-srts', metavar=mv_path, nargs='*', 
                         help='Subtitle files in .srt format')

    in_files.add_argument('-i', '--menu-imgs', metavar=mv_path, nargs='*', 
                         help='Menu images')

    in_files.add_argument('-l', '--menu-labels', metavar='LABEL', nargs='*', 
                         help='Menu labels')

    in_files.add_argument('-b', '--menu-bg', metavar=mv_path,
                         help='Menu background image')

    #

    out_files = parser.add_argument_group(title='Output locations')

    out_files.add_argument('-o', '--out-dir', metavar=mv_path,
                           help='Output directory')

    out_files.add_argument('-t', '--tmp-dir', metavar=mv_path,
                           help='Temp directory (for transcoding video files, etc.) By default /tmp, or whatever tempfile.gettempdir() returns will be used if there is enough space available.')

    out_files.add_argument('-n', '--out-name', metavar='NAME',
                           help='Base name prefix for generated files (menu, log, etc)')


    #

    in_opts = parser.add_argument_group(title='Input options')

    in_opts.add_argument('--vid-fmts', metavar='FMT', nargs='*', 
                         default=['mp4', 'avi', 'mkv'],
                         help='If in-vids are not specified, search in-dirs for video files with these extensions')

    in_opts.add_argument('--img-fmts', metavar='FMT', nargs='*', 
                         default=['png', 'jpg', 'bmp', 'gif'],
                         help='If menu-imgs are not specified, search video directories for image files with these extensions')

    in_opts.add_argument('--img-names', metavar='NAME', nargs='*', 
                         default=['poster', 'folder'],
                         help='If menu-imgs are not specified, search video directories for image files with these names (in addition to the video names themselves)')

    in_opts.add_argument('--multiple-vids-per-dir', action='store_false',
                         dest='one_vid_per_dir', default=True,
                         help='Normally, if in-vids are not specified, in-dirs are assumed to contain one video each. With this option all of the video files in each in-dir are added. Incompatible with the img-names option; images are only searched for using the name of the video')

    in_opts.add_argument('--label-from-img', action='store_true',
                         help='Infer menu-labels from menu-img filenames instead of the default of using the video filename')

    in_opts.add_argument('--label-from-dir', action='store_true',
                         help='Infer menu-labels from directory names instead of the default of using the video filename')

    in_opts.add_argument('--strip-label-year', action='store_true',
                         help='Strip parenthesized year from end of inferred labels. e.g., "label (2013)" -> "label"')

    in_opts.add_argument('--no-encode-v', action='store_true',
                         help='Skip encoding of video files.  Assume video files are DVD compliant mpeg2.')

    in_opts.add_argument('--unstack-vids', action='store_true',
                         help='Treat multiple input video files as single video when their names only differ by certain rules. e.g., "video.cd1.ext", "video.cd2.ext"')

    #

    out_opts = parser.add_argument_group(title='Output options')

    out_opts.add_argument('--no-menu', action='store_false', dest='with_menu', 
                          default=True,
                         help="Don't make a menu for the DVD")

    out_opts.add_argument('--no-author-dvd', action='store_false', 
                          dest='with_author_dvd', default=True,
                         help="Output an xml file that can be used with dvdauthor, but don't actually create the DVD files")

    out_opts.add_argument('--dvd-size', type=int, default=4700372992, 
                          dest='dvd_size_bytes', metavar='BYTES', 
                         help='Size of DVD media in bytes. The default of 4700372992 is the size of a single-layer DVD+R, which is slightly smaller than a DVD-R, so will work for either one. DVD-R=4707319808, DVD+R=4700372992, DVD-R DL=8543666176, DVD+R DL=8547991552.  (default: %(default)s)')

    #

    dvd_opts = parser.add_argument_group(title='DVD options')

    dvd_opts.add_argument('--audio-lang', metavar='LANG', default='en', 
                          help="Audio Language. (default: %(default)s)")

    dvd_opts.add_argument('--with-subs', action='store_true', default=False,
                          help="Search for matching subtitle files in the directory of each video")

    dvd_opts.add_argument('--sub-lang', metavar='LANG', default='en', 
                          help="Subtitle language. (default: %(default)s)")

    dvd_opts.add_argument('--dvd-ar', choices=['16:9', '4:3'], default=None,
                          help="DVD aspect ratio.  If not specified, it will be calculated automatically.")

    dvd_opts.add_argument('--vbitrate', metavar='BPS', type=int, 
                          help="Video bitrate in bits per second. If not specified it will be calculated automatically based on dvd-size.")

    dvd_opts.add_argument('--abitrate', metavar='BPS', type=int, 
                          default=196608,
                          help="Audio bitrate in bits per second. (default: %(default)s (192kbps))")

    dvd_opts.add_argument('--no-two-pass', action='store_false', default=True,
                          dest='two_pass',
                          help="Don't use two-pass encoding.")

    dvd_opts.add_argument('--no-separate-titlesets', action='store_false', 
                          default=True, dest='separate_titlesets',
                          help="By default, the DVD will be made with separate titlesets if there are both 4:3 and 16:9 videos present. This option overrides that behavior and puts everything in a single titleset, cropping/padding the video so that everything uses the same aspect ratio.")

    dvd_opts.add_argument('--no-separate-titles', action='store_false', 
                          default=True, dest='separate_titles',
                          help="By default every video will be placed in its own title on the DVD. This option overrides that behavior and puts everything in a single title.  Each video will be a chapter in the title.")

    #

    menu_opts = parser.add_argument_group(title='Menu options')

    menu_opts.add_argument('--menu-ar', choices=['16:9', '4:3'], default=None,
                          dest='dvd_menu_ar',
                          help="Menu aspect ratio.  If not specified, it defaults to 16:9 unless if all titles are 4:3 (or dvd-ar is forced to 4:3)")

    menu_opts.add_argument('--with-menu-labels', action='store_true', 
                           default=False, 
                           help="This option adds labels below the menu-imgs even if none are specified with the --menu-imgs option. The labels are based on the video filenames unless the --label_from_img or --label_from_img options are present.")

    menu_opts.add_argument('--label-line-height', type=int, metavar='PX', 
                           dest='menu_label_line_height', default=18,
                           help="Line height in pixels for the menu-labels. (default: %(default)s)")

    menu_opts.add_argument('--no-loop-menu', action='store_true', default=False, 
                           help="Normally the menu plays in a loop until a title is selected.  With this option the menu plays once and then starts playing the first title.")

    #

    options = parser.parse_args()
    return options

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
              #~ dvd_format=options.dvd_format, 
              dvd_ar=options.dvd_ar, 
              vbitrate=options.vbitrate, 
              abitrate=options.abitrate, 
              two_pass=options.two_pass,
              separate_titles=options.separate_titles, 
              separate_titlesets=options.separate_titlesets, 
              #~ ar_threshold=options.ar_threshold,
              # menu options
              dvd_menu_ar=options.dvd_menu_ar,
              with_menu_labels=options.with_menu_labels, 
              menu_label_line_height=options.menu_label_line_height,
              no_loop_menu=True)

def main(mode='dvd'):
    options = get_options()
    if mode == 'dvd':
        make_dvd(options)
    return 0

if __name__ == '__main__':
    main()
