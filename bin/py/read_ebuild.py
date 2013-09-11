#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys

import roverlay.util.ebuildparser

if __name__ == '__main__':
   EP = roverlay.util.ebuildparser.SrcUriParser
   for arg in sys.argv[1:]:
      parser = EP.from_file ( arg )
      print ( [ str(k) for k in parser.iter_local_files(True) ] )
