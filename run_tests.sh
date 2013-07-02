#!/bin/sh
cd "${0%/*}" || exit

TESTPY="${PWD}/run_tests.py"
first=Y

conf="${PWD}/R-overlay.conf"
tconf="${conf}.tests"

[ -e "${tconf}" ] || { ln -vs -- "${conf}" "${tconf}" && first=; } || exit

for PYTHON in python2 python3; do
   if which ${PYTHON} 1>/dev/null 2>/dev/null; then
      [ -n "${first}" ] && first= || echo
      echo "*** Running ${TESTPY##*/} with PYTHON=${PYTHON} ***"
      echo
      PYTHONPATH="${PWD}" ${PYTHON} "${TESTPY}"
   else
      echo "PYTHON=${PYTHON} not found." 1>&2
   fi
done
