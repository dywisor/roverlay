#!/bin/bash
readonly SCRIPT=$(readlink -f "${BASH_SOURCE[0]?}")
readonly SCRIPT_NAME="${BASH_SOURCE[0]##*/}"
readonly SCRIPT_DIR="${SCRIPT%/*}"

readonly PRJROOT="${SCRIPT_DIR%/*}"
readonly PYSCRIPT="${SCRIPT_DIR}/py/${SCRIPT_NAME%.*}.py"

export PYTHONPATH="${PRJROOT}${PYTHONPATH:+:}${PYTHONPATH}"


cd "${PRJROOT}" || exit

if [[ -x "${PYSCRIPT}" ]]; then
   ${PYSCRIPT} "$@"
elif [[ -f "${PYSCRIPT}" ]]; then
   ${PYTHON:-python} ${PYSCRIPT} "$@"
else
   echo "script not found: ${PYSCRIPT}" 1>&2
   exit 9
fi
