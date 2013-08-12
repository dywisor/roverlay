#!/usr/bin/roverlay-sh
#
# This script runs R overlay creation and repoman afterwards.
#
# It will exit immediately if another instance is already running.
# To achieve this, filesystem locks are used (/run/lock/roverlay.lock).
#
# So, it's safe to set up a cronjob that calls this script.
#
# Dependencies:
# * lockfile-progs (app-misc/lockfile-progs)
# * portage for repoman
# * [roverlay]
#
set -u

# --- "config" ---

# (TODO)
REPOMAN_ARGS="--pretend full"

ROVERLAY_ARGS="--strict"

# --- end of config ---



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

# void run_print_usage()
#
#  Prints the usage message.
#
run_print_usage() {
echo "Usage: ${0##*/} [option...]

options:
   -h, --help        print this message and exit
   +C, --no-create   disable overlay creation
   +S, --no-sync     disable sync (offline mode)
   +R, --no-repoman  disable repoman"
}

# @noreturn run_exit_usage ( [message], [code] )
#
#  Prints the usage message and exits afterwards.
#  Calls die() for exiting if message or code are set.
#
run_exit_usage() {
   if [ $# -eq 0 ]; then
      print_usage
      exit 0
   else
      print_usage 1>&2
      echo 1>&2
      die "$@"
   fi
}


# prepare:

WANT_ROVERLAY_CREATE=y
WANT_ROVERLAY_SYNC=y
WANT_REPOMAN=y

#  parse args
doshift=1
while [ $# -gt 0 ]; do
   case "${1?}" in
      '-h'|'--help')       run_exit_usage ;;
      '+C'|'--no-create')  WANT_ROVERLAY_CREATE=n ;;
      '+S'|'--no-sync')    WANT_ROVERLAY_SYNC=n ;;
      '+R'|'--no-repoman') WANT_REPOMAN=n ;;
      *)
         run_exit_usage "unknown arg: ${1}" ${EX_ARG_ERR?}
      ;;
   esac
   shift ${doshift} || OUT_OF_BOUNDS
   doshift=1
done
unset -v doshift

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
   trap run__cleanup TERM EXIT

   roverlay_opts=""
   roverlay_opts() { roverlay_opts="${roverlay_opts-}${roverlay_opts:+ }$*"; }

   yesno "${WANT_ROVERLAY_SYNC}" || roverlay_opts "--no-sync"

   # run roverlay
   if ${ROVERLAY_EXE} ${ROVERLAY_ARGS-} ${roverlay_opts}; then
      # success, continue with repoman
      if yesno "${WANT_REPOMAN}"; then
         (
            cd "${S}" && \
            repoman ${REPOMAN_ARGS-} 1>"${WORKDIR}/repoman.log" 2>&1
         )
      fi
   fi
else
   die "another instance is already running" 0
fi
