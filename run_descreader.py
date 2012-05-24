#!/usr/bin/env python3
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import sys

import roverlay.fileio

reader = roverlay.fileio.DescriptionReader()

for descfile in sys.argv[1:]:
	reader.readfile ( descfile )


