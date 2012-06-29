#!/usr/bin/env python3

import sys
import logging
import os.path

ARGV = sys.argv[1:]

from roverlay.rpackage import descriptionreader as d

doinfo = d.make_desc_packageinfo
Reader = d.DescriptionReader
LOGGER = logging.getLogger()

if not ARGV:
	ARGV = ( '/home/andre/tmp/R_overlay_2012-06-28/desc-files/ENmisc_1.2.4.desc', )


for df in ARGV:
	df = os.path.abspath ( df )
	pinfo = doinfo ( df )

	r = Reader ( pinfo, LOGGER, read_now=False, write_desc=False )

	x = r.get_desc()
