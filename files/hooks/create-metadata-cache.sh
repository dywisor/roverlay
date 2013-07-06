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

# void cleanup()
#
cleanup() {
   trap - INT TERM EXIT
   if [ -d "${MY_CACHE_DIR-}" ]; then
      rm -rf "${MY_CACHE_DIR}"
   fi
}
MY_CACHE_DIR="${T}/egencache.$$"
autodie dodir "${MY_CACHE_DIR}"
trap cleanup INT TERM EXIT

# --portdir, --portdir-overlay?
#  using --portdir-overlay
# --jobs=?
# --rsync?
# --tolerant?
# --update [<pkg>...]?
#
autodie ${EGENCACHE} --ignore-default-opts --update --tolerant \
   --cache-dir="${MY_CACHE_DIR}" \
   --portdir-overlay="${OVERLAY}" --repo="${OVERLAY_NAME}"
autodie cleanup
