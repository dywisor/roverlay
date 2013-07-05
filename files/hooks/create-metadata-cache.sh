#!/bin/sh
# -*- coding: utf-8 -*-
# roverlay hook that updates the metadata cache
#
# should be run before "exporting" the overlay (git-commit-overlay.sh etc.)
#
set -u

## load core functions
. "${FUNCTIONS?}" || exit
#dont_run_as_root

## load helper functions
#$lf ...

: ${EGENCACHE:=egencache}
#autodie qwhich "${EGENCACHE}"

# --portdir, --portdir-overlay?
#  using --portdir-overlay
# --jobs=?
# --rsync?
# --tolerant?
# --update [<pkg>...]?
#
autodie ${EGENCACHE} --ignore-default-opts --update --tolerant \
   --portdir-overlay="${OVERLAY}" --repo="${OVERLAY_NAME}"
