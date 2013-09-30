#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#  Copyright (c) 2013 William Adams
#  Distributed under the terms of the Modified BSD License.
#  The full license is in the file LICENSE, distributed with this software.

import izdvd.main
from izdvd import config
from lxml import html as _html, etree

MODE_NAMES = {'dvd':  'izdvd',
              'menu': 'izdvdmenu',
              'bg':   'izdvdbg'}


def export_html(path, mode='dvd', width=100):
    help_doc = izdvd.main.export_help(mode=mode, width=width)
    doc_title = '{} Usage: {}'.format(MODE_NAMES[mode], config.PROG_NAME)
    doc_doctype = ('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"'
                   '    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">')

    html = _html.Element('html')
    html.set('xmlns', "http://www.w3.org/1999/xhtml")
    html.set('xml:lang', "en")
    html.set('lang', "en")
    head = _html.etree.SubElement(html, 'head')
    title = _html.etree.SubElement(head, 'title')
    title.text = doc_title
    meta = _html.etree.SubElement(head, 'meta')
    meta.set('http-equiv', "content-type")
    meta.set('content', "text/html;charset=utf-8")
    
    body = _html.etree.SubElement(html, 'body')
    a_index = _html.etree.SubElement(head, 'a', href="index.html")
    a_index.text = '{} Documentation'.format(config.PROG_NAME)
    body.append(_html.Element('hr'))
    h1 = _html.etree.SubElement(body, 'h1')
    h1.text = MODE_NAMES[mode]
    pre = _html.etree.SubElement(body, 'pre')
    pre.text = help_doc
    body.append(_html.Element('hr'))
    a_home = _html.etree.SubElement(body, 'a', 
                                    href=config.PROG_URL)
    a_home.text = config.PROG_URL
    with open(path, 'w') as f:
        f.write(etree.tostring(html, encoding=str, pretty_print=True, 
                                    doctype=doc_doctype, method='xml'))


def main(width=100):
    for i in zip(['izdvd.html', 'izdvdmenu.html', 'izdvdbg.html'], 
                 ['dvd', 'menu', 'bg']):
        export_html(i[0], mode=i[1], width=width)
    return 0

if __name__ == '__main__':
    main()

