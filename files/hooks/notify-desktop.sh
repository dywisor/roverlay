#!/bin/sh
# -*- coding: utf-8 -*-
#
#  Sends a desktop notification.
#
set -u

## load core functions
. "${FUNCTIONS?}" || exit
#dont_run_as_root

qwhich notify-send || die_cannot_run "notify-send is not available."

## load helper functions
#$lf ...

# hook body starts here

#  roverlay's hook environment doesn't pass $DISPLAY, set it here
: ${DISPLAY:=:0.0}
export DISPLAY
run_command_logged notify-send -t 10000 roverlay "done" || true
