#!/bin/sh
# -*- coding: utf-8 -*-
# R overlay -- shell functions
# Copyright (C) 2013 André Erdmann <dywi@mailerd.de>
# Distributed under the terms of the GNU General Public License;
# either version 2 of the License, or (at your option) any later version.
#
#
# Notes:
# * no bashisms here
#
#
# --- functions provided by this file ---
#
# message:
# void veinfo ( message )
# void einfo  ( message )
# void ewarn  ( message )
# void eerror ( message )
#
# core:
# @noreturn die ( [message], [exit_code] ), raises exit()
# @noreturn OUT_OF_BOUNDS(), raises die()
# int  run_command        ( *cmdv )
# int  run_command_logged ( *cmdv )
# void autodie            ( *cmdv ), raises die()
#
# void load_functions ( *filenames, **SHLIB ), raises die()
# void dont_run_as_root(), raises die()
# int  list_has ( word, *list_items )
# int  qwhich ( *command )
#
# fs util:
# int dodir ( *dir )
#
# str util:
# int  yesno     ( word, **YESNO_YES=0, **YESNO_NO=1, **YESNO_EMPTY=2 )
# ~int str_strim ( *args )
# ~int str_upper ( *args )
# ~int str_lower ( *args )
# ~int str_field ( fieldspec, *args, **FIELD_SEPARATOR=' ' )
#
# int util:
# @intcheck is_int()
# @intcheck is_natural()
# @intcheck is_positive()
# @intcheck is_negative()
#
#
# --- variables provided by this file ---
#
# IFS_DEFAULT
# IFS_NEWLINE
#
# DEVNULL
#
# EX_ERR
# EX_ARG_ERR
#
# SCRIPT_FILENAME
# SCRIPT_NAME
#
# lf
#  "reference" to load_functions()
#
# @private __HAVE_CORE_FUNCTIONS__
#
# --- END HEADER ---

if [ -z "${__HAVE_CORE_FUNCTIONS__-}" ]; then
readonly __HAVE_CORE_FUNCTIONS__=y

## make some env vars readonly

readonly FUNCTIONS
[ -z "${SHLIB-}" ] || readonly SHLIB

readonly DEBUG VERBOSE QUIET NO_COLOR

readonly ROVERLAY_PHASE \
   OVERLAY S \
   DISTROOT \
   TMPDIR T \
   ADDITIONS_DIR FILESDIR \
   EBUILD NOSYNC


## vars / constants

readonly IFS_DEFAULT="${IFS}"
readonly IFS_NEWLINE='
'

: ${DEVNULL:=/dev/null}
readonly DEVNULL

readonly EX_ERR=2
readonly EX_ARG_ERR=5

readonly SCRIPT_FILENAME="${0##*/}"
readonly SCRIPT_NAME="${SCRIPT_FILENAME%.*}"

readonly lf=load_functions


## message functions

# void veinfo ( message ) [**DEBUG]
#
if [ "${DEBUG:?}" = "y" ]; then
   veinfo() { echo "$*"; }
else
   veinfo() { return 0; }
fi

# void einfo ( message ) [**VERBOSE]
#
if [ "${VERBOSE:?}" = "y" ]; then
   einfo() { echo "$*"; }
else
   einfo() { return 0; }
fi

# void ewarn ( message ) [**QUIET]
#
if [ "${QUIET:?}" != "y" ]; then
   ewarn() { echo "$*" 1>&2; }
else
   ewarn() { return 0; }
fi

# void eerror ( message )
#
eerror() { echo "$*" 1>&2; }


## core functions

# @noreturn die ( [message], [exit_code=**EX_ERR] ), raises exit (exit_code)
#
#  Prints a message to stderr and exits afterwards.
#
die() {
   if [ -n "${1-}" ]; then
      eerror "died: ${1}"
   else
      eerror "died."
   fi
   exit "${2:-${EX_ERR?}}"
}

# @noreturn OUT_OF_BOUNDS(), raises die (**EX_ARG_ERR)
#
#  Catches non-zero shift return and calls die().
#
OUT_OF_BOUNDS() { die "shift returned non-zero." ${EX_ARG_ERR?}; }

# int run_command ( *cmdv )
#
#  Runs a command and passes its return value. Also logs the command.
#
run_command() {
   veinfo "running command: $*"
   "$@"
}

# int run_command_logged ( *cmdv )
#
#  Runs a command and passes its return value. Also logs the command + result.
#
run_command_logged() {
   local rc=0
   veinfo "running command: $*"
   "$@" || rc=${?}
   if [ ${rc} -eq 0 ]; then
      veinfo "command succeeded."
      return 0
   else
      einfo "command '$*' returned ${rc}."
      return ${rc}
   fi
}

# void autodie ( *cmdv ), raises die()
#
#  Executes a commands. Dies on non-zero return code.
#
autodie() {
   local rc=0
   veinfo "running command: $*"
   "$@" || rc=$?
   if [ ${rc} -eq 0 ]; then
      return 0
   else
      die "command '$*' returned ${rc}" ${rc}
   fi
}

# void load_functions ( *filenames, **SHLIB ), raises die()
#
#  Loads zero or more additional shell function files from $SHLIB.
#  Dies if a file cannot be sourced.
#
load_functions() {
   [ -n "${SHLIB-}" ] || die "\$SHLIB is not set."
   local f
   while [ $# -gt 0 ]; do
      f="${SHLIB}/${1%.sh}.sh"
      veinfo "Trying to load functions file ${f} ... "
      . "${f}" || die "failed to load functions file ${f}."
      shift
   done
   return 0
}

# void dont_run_as_root(), raises die()
#
#  Dies if this process is run as root.
#
dont_run_as_root() {
   local uid=$(id -ru)
   if [ -z "${uid}" ]; then
      die "cannot get \$uid."
   elif [ ${uid} -ne 0 2>>${DEVNULL} ]; then
      return 0
   else
      die "bad \$uid ${uid}."
   fi
}

# int list_has ( word, *list_items )
#
#  Returns true if word is in list_items, else false.
#
list_has() {
   local kw="${1}"
   shift || OUT_OF_BOUNDS

   while [ $# -gt 0 ]; do
      [ "x${kw}" != "x${1}" ] || return 0
      shift
   done
   return 1
}

# int qwhich ( *command )
#
#  Returns true if 'which' finds all listed commands, else false.
#
qwhich() {
   while [ $# -gt 0 ]; do
      which "${1}" 1>>${DEVNULL} 2>>${DEVNULL} || return 1
      shift
   done
   return 0
}

## fs util functions

# int dodir ( *dir )
#
#  Ensures that the given directories exist by creating them if necessary.
#
#  Returns the number of directories that could not be created.
#
dodir() {
   local fail=0
   while [ $# -gt 0 ]; do
      [ -d "${1}" ] || mkdir -p -- "${1}" || fail=$(( ${fail} + 1 ))
      shift
   done
   return ${fail}
}


## str util functions

# int yesno ( word, **YESNO_YES=0, **YESNO_NO=1, **YESNO_EMPTY=2 )
#
#  Returns:
#  * YESNO_YES   (0) if word means yes
#  * YESNO_EMPTY (2) if word is empty
#  * YESNO_NO    (1) otherwise (word is not empty and does not mean yes)
#
yesno() {
   case "${1-}" in
      '')
         return ${YESNO_EMPTY:-2}
      ;;
      # yes | y | true | 1 | enable(d) | on
      [yY][eE][sS]|\
      [yY]|\
      [tT][rR][uU][eE]|\
      1|\
      [eE][nN][aA][bB][lL][eE]?|\
      [oO][nN]\
      )
         return ${YESNO_YES:-0}
      ;;
      *)
         return ${YESNO_NO:-1}
      ;;
   esac
}

# ~int str_trim ( *args )
#
#  Removes whitespace at the beginning + end of a string
#  and replaces any whitespace sequence within the string
#  with a single space char.
#
str_trim() { sed -r -e 's,^\s+,,' -e 's,\s+$,,' -e 's,\s+, ,g' "$@"; }

# ~int str_upper ( *args )
str_upper() { tr [:lower:] [:upper:] "$@"; }

# ~int str_lower ( *args )
str_lower() { tr [:upper:] [:lower:] "$@"; }

# ~int str_field ( fieldspec, *args, **FIELD_SEPARATOR=' ' )
#
str_field() { cut -d "${FIELD_SEPARATOR:- }" -f "$@"; }


## int util functions

# @funcdef shbool @intcheck [<condition>:=true] <function name> ( word )
#
#   Returns true if word is a number and condition(word) evaluates to true.
#

# @intcheck is_int()
is_int() {
   [ -n "${1-}" ] || return 1
   [ "${1}" -ge 0 2>>${DEVNULL} ] || [ "${1}" -lt 0 2>>${DEVNULL} ]
}

# @intcheck >=0 is_natural()
is_natural()  { [ -n "${1-}" ] && [ "${1}" -ge 0 2>>${DEVNULL} ]; }

# @intcheck >0 is_positive()
is_positive() { [ -n "${1-}" ] && [ "${1}" -gt 0 2>>${DEVNULL} ]; }

# @intcheck <0 is_negative()
is_negative() { [ -n "${1-}" ] && [ "${1}" -lt 0 2>>${DEVNULL} ]; }

fi
