# R Overlay
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

logging.basicConfig (
	level=logging.DEBUG,
	filename='roverlay.log',
	filemode='a',
	format='%(asctime)s %(levelname)-8s %(name)-14s -- %(message)s',
	datefmt='%F %H:%M:%S'
)

# add console output to the logger
ch = logging.StreamHandler()
ch.setLevel ( logging.INFO )
ch.setFormatter (
	logging.Formatter  ( '%(levelname)-8s %(name)-14s -- %(message)s' )
)
logging.getLogger().addHandler ( ch )
del ch

VERSION = "0.0-pre1"
