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

# a valid PORTDIR is required
[ -d "${PORTDIR-}" ] || die "\$PORTDIR '${PORTDIR-}' does not exist."

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

# inlined repos.conf for egencache
MY_REPO_CONFIG="
[DEFAULT]
main-repo = gentoo

[gentoo]
location = ${PORTDIR}

[${OVERLAY_NAME}]
location = ${OVERLAY}"


# --portdir, --portdir-overlay?
#  using --repositories-configuration as
#   --portdir-overlay is considered deprecated
#
# --jobs=?
# --rsync?
# --tolerant?
# --update [<pkg>...]?
#
autodie ${EGENCACHE} --ignore-default-opts --update --tolerant \
   --cache-dir="${MY_CACHE_DIR}" \
   --repositories-configuration="${MY_REPO_CONFIG}" \
   --repo="${OVERLAY_NAME}"
autodie cleanup
