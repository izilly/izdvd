Description
===========

Izdvd is a set of python scripts for authoring DVDs and/or DVD menus with 
little or no user interaction.

Three scripts are included:

    **izdvd**
        Outputs an authored DVD with a simple menu made from images 
        (thumbnails, posters, etc) corresponding to each video laid out in a 
        grid.
        
        Input can be given as video files or directories containing 
        video files. If you have image with filenames similar 
        to the videos, or videos in separate folders with images named like 
        "folder.jpg", "poster.png", etc, then it will find the images to use 
        for the menu automatically.  Subtitles can be searched for and added
        to the DVD in the same way if desired.
        
        Optionally, labels can be placed under each menu image.  These can be 
        inferred automatically from the video, directory or image name, or they 
        can be explicitly specified on the command line.
    
    **izdvdmenu**
        Outputs a DVD menu (a set of video and xml files that can be used to 
        create a DVD with dvdauthor)
    
    **izdvdbg**
        Outputs a set of image and xml files that can be used to create a DVD 
        menu with spumux (part of the dvdauthor package)


Requirements
============

* Linux
* Python 3.x
* python-lxml
* ffmpeg
* imagemagick
* dvdauthor
* mjpegtools
* mediainfo
* toolame
* mplayer (optional; for previewing videos/menus)


License
=======

* Copyright (c) 2013 William Adams
* Distributed under the terms of the Modified BSD License.
* The full license is in the file LICENSE, distributed with this software.


Installation
============

Download the source from::

    https://github.com/izzilly/izdvd

Then run::

    python setup.py
