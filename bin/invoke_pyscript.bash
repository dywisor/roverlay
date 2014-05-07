#!/bin/bash
readonly SCRIPT="$(readlink -f "${BASH_SOURCE[0]?}")"
readonly SCRIPT_FILENAME="${BASH_SOURCE[0]##*/}"
readonly SCRIPT_DIR="${SCRIPT%/*}"
readonly PRJROOT="${SCRIPT_DIR%/*}"

extra_args=()

SCRIPT_NAME="${SCRIPT_FILENAME%.py}"
case "${SCRIPT_NAME}" in
   *[-_.]others)
      export ROVERLAY_TARGET_TYPE="foreign"
      SCRIPT_NAME="${SCRIPT_NAME%[-_.]*}"
   ;;
   *)
      : ${ROVERLAY_TARGET_TYPE:=gentoo}
      SCRIPT_NAME="${SCRIPT_NAME}"
   ;;
esac

case "${SCRIPT_NAME}" in
   'roverlay') SCRIPT_NAME="main" ;;
esac
readonly SCRIPT_NAME

if [[ "${ROVERLAY_TARGET_TYPE}" == "foreign" ]]; then
   case "${SCRIPT_NAME#roverlay[_-]}" in
      'setup')
         extra_args+=( '--target-type' 'foreign' "$@" )
      ;;
      'main'|'query'[-_]'config'|'status')
         extra_args+=( '-c' "${PRJROOT}/R-overlay.conf.others" "$@" )
      ;;
   esac
fi

readonly PYSCRIPT="${SCRIPT_DIR}/py/${SCRIPT_NAME}.py"
[ ${#extra_args[@]} -eq 0 ] || set -- "${extra_args[@]}" "$@"

export ROVERLAY_PRJROOT="${PRJROOT}"
export PYTHONPATH="${PRJROOT}${PYTHONPATH:+:}${PYTHONPATH}"


cd "${PRJROOT}" || exit

if [[ -z "${PYTHON-}" ]] && [[ -x "${PYSCRIPT}" ]]; then
   exec ${PYSCRIPT} "$@"
elif [[ -f "${PYSCRIPT}" ]]; then
   exec ${PYTHON:-python} ${PYSCRIPT} "$@"
else
   echo "script not found: ${PYSCRIPT}" 1>&2
   exit 9
fi
