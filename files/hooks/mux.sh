#!/bin/sh
# -*- coding: utf-8 -*-
# simple roverlay hook that runs other hooks (by sourcing them)
#
set -u

LC_COLLATE=C
export LC_COLLATE

LC_CTYPE=C
export LC_CTYPE

## load core functions
. "${FUNCTIONS?}" || exit
#dont_run_as_root


## load $ROVERLAY_HOOKRC (if set)
if [ -n "${ROVERLAY_HOOKRC-}" ]; then
   . "${ROVERLAY_HOOKRC}" || \
      die "failed to load ROVERLAY_HOOKRC (${ROVERLAY_HOOKRC})."
fi

# tmpdir should exist (assuming that hooks don't remove this dir)
autodie dodir "${T}"

for hookfile in \
   ${FILESDIR}/hooks/${ROVERLAY_PHASE}/?*.sh \
   ${FILESDIR}/hooks/?*.${ROVERLAY_PHASE}
do
   if [ -f "${hookfile}" ]; then
      #subshell?
      #( . "${hookfile}"; ) || ...

      veinfo "Running hook '${hookfile##*/}'"

      # initial directory should always be $S
      cd "${S}" && . "${hookfile}" || \
         die "errors occured while running hook '${hookfile}'"

      # restore signals
      trap - INT TERM EXIT
   fi
done

rmdir "${T}" 2>>${DEVNULL} || true
