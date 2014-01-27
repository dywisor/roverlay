#!/bin/bash
readonly SCRIPT="$(readlink -f "${BASH_SOURCE[0]?}")"
readonly SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
readonly SCRIPT_DIR="${SCRIPT%/*}"

readonly PRJROOT="${SCRIPT_DIR%/*}"
readonly REAL_SCRIPT="${SCRIPT_DIR}/scripts/${SCRIPT_NAME%.*}.sh"

export ROVERLAY_PRJROOT="${PRJROOT}"
export X_RV_QUERY_CONFIG="${PRJROOT}/bin/query_config"

cd "${PRJROOT}" || exit

if [[ -x "${REAL_SCRIPT}" ]]; then
   exec ${REAL_SCRIPT} "$@"
elif [[ -f "${REAL_SCRIPT}" ]]; then
   exec ${SHELL:-sh} ${REAL_SCRIPT} "$@"
else
   echo "script not found: ${REAL_SCRIPT}" 1>&2
   exit 9
fi
