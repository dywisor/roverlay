#!/usr/bin/roverlay-sh
#
# This script runs R overlay creation and repoman afterwards.
#
# It will exit immediately if another instance is already running.
# To achieve this, filesystem locks are used (/run/lock/roverlay.lock).
#
# So, it's safe to set up a cronjob that calls this script.
#
set -u

# reset DEBUG, VERBOSE, QUIET
DEBUG=n; QUIET=n; VERBOSE=y

LC_COLLATE=C

. "${FUNCTIONS?}" || exit 9

readonly MY_LOCK=/run/lock/roverlay
MY_LOCK_PID=

# void run__cleanup ( **MY_LOCK_PID!, **MY_LOCK )
#
#  Atexit function that releases the lock.
#
run__cleanup() {
   # release trap
   trap - INT TERM EXIT

   # release lock
   if [ -n "${MY_LOCK_PID-}" ]; then
      kill "${MY_LOCK_PID}"
      wait "${MY_LOCK_PID}" 2>>${DEVNULL} && MY_LOCK_PID=
   fi
   lockfile-remove "${MY_LOCK}" || true
}


# prepare:

# (TODO)
REPOMAN_ARGS="--pretend full"

WANT_ROVERLAY_CREATE=y
WANT_ROVERLAY_SYNC=y
WANT_REPOMAN=y

#  parse args
doshift=1
while [ $# -gt 0 ]; do
   case "${1?}" in
      '+C'|'--no-create') WANT_ROVERLAY_CREATE=n ;;
      '+S'|'--no-sync') WANT_ROVERLAY_SYNC=n ;;
      '+R'|'--no-repoman') WANT_REPOMAN=n ;;
      *)
         die "unknown arg: ${1}" ${EX_ARG_ERR?}
      ;;
   esac
   shift ${doshift} || OUT_OF_BOUNDS
   doshift=1
done
unset -v doshift

# anything to do?

# main:
#
#  anything to do? acquire lock
if ! list_has y \
   "${WANT_ROVERLAY_CREATE}" "${WANT_ROVERLAY_SYNC}" "${WANT_REPOMAN}"
then
   die 'nothing to do' 2
elif lockfile-create --retry 0 "${MY_LOCK}" 2>>${DEVNULL}; then
   # hold lock until done
   lockfile-touch "${MY_LOCK}" &
   MY_LOCK_PID="$!"
   trap run__cleanup INT TERM EXIT

   roverlay_opts=""
   roverlay_opts() { roverlay_opts="${roverlay_opts-}${roverlay_opts:+ }$*"; }

   ! yesno "${WANT_ROVERLAY_SYNC}" || roverlay_opts "--nosync"

   # run roverlay
   if ${ROVERLAY_EXE} ${roverlay_opts}; then
      # success, continue with repoman
      if yesno "${WANT_REPOMAN}"; then
         ( cd "${S}" && repoman ${REPOMAN_ARGS} 2>&1 1>"${WORKDIR}/repoman.log"; )
      fi
   fi
else
   die "another instance is already running" 0
fi
