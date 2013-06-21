#!/bin/sh
# -*- coding: utf-8 -*-
# simple roverlay hook that runs other hooks (by sourcing them)
#
set -u

## load core functions
. "${FUNCTIONS?}" || exit
#dont_run_as_root

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
