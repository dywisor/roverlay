#!/bin/bash
set -u
SCRIPT=$(readlink -f "${BASH_SOURCE[0]?}")
SCRIPT_DIR="${SCRIPT%/*}"
PRJROOT="${SCRIPT_DIR%/*}"

export ROVERLAY_PRJROOT="${PRJROOT}"

readonly ROVERLAY_SETUP="${PRJROOT}/bin/roverlay-setup"
readonly FUNCTIONS="${PRJROOT}/files/shlib/functions.sh"
readonly FUNCTIONS_STANDALONE='y'
readonly ROVERLAY_INSTALLED='n'

unset -v SCRIPT SCRIPT_DIR PRJROOT
. "${FUNCTIONS}" || exit 0
$lf setup-interactive

setup_interactive_main "$@"
