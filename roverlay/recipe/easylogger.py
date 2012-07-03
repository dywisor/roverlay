# R Overlay
# Copyright 2006-2012 Gentoo Foundation
# Distributed under the terms of the GNU General Public License v2

import logging

_STATUS = 0

def setup ( conf ):
	global _STATUS
	if _STATUS > 1:
		return

	logging.basicConfig (
		level=logging.DEBUG,
		filename=conf.get ( [ 'LOG', 'FILE', 'main' ], 'roverlay.log' ),
		filemode='a',
		format='%(asctime)s %(levelname)-8s %(name)-14s -- %(message)s',
		datefmt='%F %H:%M:%S'
	)

	# add console output to the logger
	ch = logging.StreamHandler()
	ch.setLevel ( logging.DEBUG )
	ch.setFormatter (
		logging.Formatter  ( '%(levelname)-8s %(name)-14s -- %(message)s' )
	)
	logging.getLogger().addHandler ( ch )

	_STATUS = 2

def setup_initial():
	global _STATUS
	if _STATUS > 0:
		return

	pass

	_STATUS = 1
